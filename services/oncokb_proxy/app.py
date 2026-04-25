"""OncoKB proxy — FastAPI app holding the OncoKB API token server-side.

Architecture (per docs/plans/oncokb_integration.md):

  Pyodide engine  ──fetch──▶  this proxy (Cloud Run)  ──auth──▶  OncoKB API
                                       │
                                       └── in-memory LRU cache, 7-day TTL

The Pyodide client never sees the token. Each lookup is keyed on
(gene, variant, disease_oncotree_code, tumor_type) and cached.

Out-of-scope for this scaffold (deferred):
  - Deployment (Cloud Run service.yaml, secret manager, IAM).
  - Real OncoKB call (mocked in tests; live-API hookup behind ENV flag).
  - Render-side integration in render_plan_html (separate Phase).
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ONCOKB_API_BASE = os.environ.get("ONCOKB_API_BASE", "https://www.oncokb.org/api/v1")
ONCOKB_API_TOKEN = os.environ.get("ONCOKB_API_TOKEN")
CACHE_TTL_SECONDS = int(os.environ.get("ONCOKB_CACHE_TTL_SECONDS", 7 * 24 * 3600))
CACHE_MAX_ENTRIES = int(os.environ.get("ONCOKB_CACHE_MAX_ENTRIES", 4096))
LIVE_MODE = os.environ.get("ONCOKB_LIVE", "0") == "1"

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ONCOKB_PROXY_CORS_ORIGINS",
        "https://openonco.org,http://localhost:8000,http://localhost:3000",
    ).split(",")
    if o.strip()
]


app = FastAPI(
    title="OpenOnco · OncoKB Proxy",
    description=(
        "Read-only server-side proxy for OncoKB therapeutic-level lookups. "
        "Holds the OncoKB API token; Pyodide client calls this proxy instead "
        "of the OncoKB API directly."
    ),
    version="0.1.0-scaffold",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^http://localhost(:\d+)?$",
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)


# ── Cache ────────────────────────────────────────────────────────────────


class _LRU:
    """Tiny LRU with TTL. Sufficient for ~4k entries; swap for redis if scaled."""

    def __init__(self, maxsize: int, ttl_seconds: int) -> None:
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._d: "OrderedDict[tuple, tuple[float, dict]]" = OrderedDict()

    def get(self, key: tuple) -> Optional[dict]:
        item = self._d.get(key)
        if item is None:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            self._d.pop(key, None)
            return None
        self._d.move_to_end(key)
        return value

    def set(self, key: tuple, value: dict) -> None:
        self._d[key] = (time.time(), value)
        self._d.move_to_end(key)
        while len(self._d) > self.maxsize:
            self._d.popitem(last=False)

    def __len__(self) -> int:
        return len(self._d)


_cache = _LRU(CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS)


# ── Models ───────────────────────────────────────────────────────────────


class LookupRequest(BaseModel):
    gene: str = Field(..., min_length=1, max_length=32)
    variant: str = Field(..., min_length=1, max_length=128)
    oncotree_code: Optional[str] = Field(None, max_length=32)
    tumor_type: Optional[str] = Field(None, max_length=128)


class TherapeuticOption(BaseModel):
    level: str  # "1" | "2" | "3A" | "3B" | "4" | "R1" | "R2"
    drugs: list[str]
    description: Optional[str] = None
    pmids: list[str] = Field(default_factory=list)


class LookupResponse(BaseModel):
    gene: str
    variant: str
    oncokb_url: str
    therapeutic_options: list[TherapeuticOption]
    cached: bool


# ── Endpoints ────────────────────────────────────────────────────────────


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "live_mode": LIVE_MODE,
        "token_configured": bool(ONCOKB_API_TOKEN),
        "cache_size": len(_cache),
        "cache_max": CACHE_MAX_ENTRIES,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "allowed_origins": ALLOWED_ORIGINS,
    }


@app.post("/lookup", response_model=LookupResponse)
async def lookup(req: LookupRequest, request: Request) -> LookupResponse:
    key = (req.gene.upper(), req.variant, req.oncotree_code or "", req.tumor_type or "")

    cached = _cache.get(key)
    if cached is not None:
        return LookupResponse(**cached, cached=True)

    if not LIVE_MODE:
        # Scaffold mode — synthesize an empty response so end-to-end works
        # without an OncoKB token. Tests use this path.
        result = {
            "gene": req.gene.upper(),
            "variant": req.variant,
            "oncokb_url": _oncokb_gene_url(req.gene, req.variant),
            "therapeutic_options": [],
        }
        _cache.set(key, result)
        return LookupResponse(**result, cached=False)

    if not ONCOKB_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="ONCOKB_LIVE=1 but ONCOKB_API_TOKEN is unset.",
        )

    result = await _call_oncokb(req)
    _cache.set(key, result)
    return LookupResponse(**result, cached=False)


# ── Internals ────────────────────────────────────────────────────────────


def _oncokb_gene_url(gene: str, variant: str) -> str:
    return f"https://www.oncokb.org/gene/{gene.upper()}/{variant}"


async def _call_oncokb(req: LookupRequest) -> dict:
    """Live OncoKB call. Returns the trimmed-down LookupResponse-shaped dict.

    OncoKB's /annotate/mutations/byProteinChange endpoint shape:
      GET ?hugoSymbol={gene}&alteration={variant}&tumorType={tumor_type}
    Authorization: Bearer {token}

    We extract `treatments` from the response and reshape into our
    therapeutic_options list. Anything beyond that is dropped (per
    src_oncokb.yaml scope: therapeutic levels only)."""

    headers = {
        "Authorization": f"Bearer {ONCOKB_API_TOKEN}",
        "Accept": "application/json",
    }
    params: dict[str, str] = {
        "hugoSymbol": req.gene.upper(),
        "alteration": req.variant,
    }
    if req.tumor_type:
        params["tumorType"] = req.tumor_type

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{ONCOKB_API_BASE}/annotate/mutations/byProteinChange",
            params=params,
            headers=headers,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"OncoKB returned {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()

    options: list[dict] = []
    for tx in data.get("treatments", []) or []:
        options.append(
            {
                "level": str(tx.get("level") or "").replace("LEVEL_", "") or "?",
                "drugs": [d.get("drugName", "") for d in tx.get("drugs", []) or []],
                "description": tx.get("description") or None,
                "pmids": [str(p) for p in tx.get("pmids", []) or []],
            }
        )

    return {
        "gene": req.gene.upper(),
        "variant": req.variant,
        "oncokb_url": _oncokb_gene_url(req.gene, req.variant),
        "therapeutic_options": options,
    }

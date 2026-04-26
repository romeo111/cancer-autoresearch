"""OncoKB proxy client — Protocol + sync implementations.

Engine is sync (`generate_plan()` is a plain function), so this client
is sync too. The proxy itself is async FastAPI; we hit it with
`httpx.Client.post(...)` per query.

Per safe-rollout v3 §0 invariant 3 (fail-open): every method swallows
network errors and returns OncoKBError instead of raising. Engine never
crashes because of OncoKB.

Per safe-rollout v3 §6 + §10: this module is the architectural firewall.
It MUST NOT be imported by:
  - knowledge_base/engine/algorithm_eval.py
  - knowledge_base/engine/redflag_eval.py
  - knowledge_base/engine/_actionability.py
  - any code path inside `generate_plan` BEFORE `tracks` is finalized

The import-graph invariant test in tests/test_oncokb_invariants.py
locks this contract.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .oncokb_types import (
    OncoKBError,
    OncoKBQuery,
    OncoKBResult,
    OncoKBTherapeuticOption,
)


class OncoKBClient(Protocol):
    """Sync client interface. Implementations must satisfy fail-open
    contract: per-query errors return OncoKBError, never raise."""

    def lookup(self, query: OncoKBQuery) -> OncoKBResult | OncoKBError: ...

    def batch_lookup(
        self, queries: list[OncoKBQuery]
    ) -> list[OncoKBResult | OncoKBError]: ...


# ── Null client (default — when engine is invoked without OncoKB) ────────


class NullOncoKBClient:
    """Returns disabled-error for every query. Used as default when
    OncoKB integration is off or proxy URL is unset."""

    def lookup(self, query: OncoKBQuery) -> OncoKBError:
        return OncoKBError(query=query, error_kind="disabled", detail="OncoKB integration disabled")

    def batch_lookup(self, queries: list[OncoKBQuery]) -> list[OncoKBError]:
        return [self.lookup(q) for q in queries]


# ── Stub client (tests — fixture-driven, no I/O) ─────────────────────────


class StubOncoKBClient:
    """Test client with a pre-baked response map keyed by (gene, variant).
    Anything not in the map returns an empty (negative) result.

    Usage:
        stub = StubOncoKBClient({
            ("BRAF", "V600E"): [
                {"level": "1", "drugs": ["vemurafenib"], "description": "...", "pmids": []},
            ],
            ("EGFR", "T790M"): [
                {"level": "R1", "drugs": ["gefitinib"], "description": "resistance", "pmids": ["123"]},
            ],
        })
    """

    def __init__(
        self,
        responses: dict[tuple[str, str], list[dict]],
        oncokb_data_version: str | None = "stub-v1.0",
    ) -> None:
        self._responses = {(k[0].upper(), k[1]): v for k, v in responses.items()}
        self._data_version = oncokb_data_version

    def lookup(self, query: OncoKBQuery) -> OncoKBResult:
        key = (query.gene.upper(), query.variant)
        raw_options = self._responses.get(key, [])
        options = tuple(
            OncoKBTherapeuticOption(
                level=str(o.get("level", "?")),
                drugs=tuple(o.get("drugs", [])),
                description=o.get("description"),
                pmids=tuple(str(p) for p in o.get("pmids", [])),
                fda_approved=bool(o.get("fda_approved", False)),
                fda_approval_year=o.get("fda_approval_year"),
            )
            for o in raw_options
        )
        return OncoKBResult(
            query=query,
            oncokb_url=f"https://www.oncokb.org/gene/{query.gene}/{query.variant}",
            therapeutic_options=options,
            cached=False,
            oncokb_data_version=self._data_version,
        )

    def batch_lookup(self, queries: list[OncoKBQuery]) -> list[OncoKBResult]:
        return [self.lookup(q) for q in queries]


# ── Httpx client (CLI / Cloud / build-time) ──────────────────────────────


class HttpxOncoKBClient:
    """Sync client that hits the OncoKB proxy via httpx.

    Per fail-open contract: timeouts, 4xx, 5xx, parse errors → OncoKBError.
    Never raises. Caller (engine) treats OncoKBError list as "section
    skipped, surface degraded warning"."""

    def __init__(
        self,
        proxy_url: str,
        *,
        timeout_seconds: float = 5.0,
        request_id_prefix: str = "engine",
    ) -> None:
        self.proxy_url = proxy_url.rstrip("/")
        self.timeout = timeout_seconds
        self._req_prefix = request_id_prefix

    def lookup(self, query: OncoKBQuery) -> OncoKBResult | OncoKBError:
        payload = {
            "gene": query.gene,
            "variant": query.variant,
        }
        if query.oncotree_code:
            payload["oncotree_code"] = query.oncotree_code
            payload["tumor_type"] = query.oncotree_code
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": f"{self._req_prefix}-{query.gene}-{query.variant}",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.proxy_url}/lookup",
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as e:
            return OncoKBError(query=query, error_kind="timeout", detail=str(e)[:200])
        except Exception as e:  # noqa: BLE001 — fail-open
            return OncoKBError(query=query, error_kind="http_error", detail=str(e)[:200])

        if resp.status_code != 200:
            return OncoKBError(
                query=query,
                error_kind="http_error",
                detail=f"proxy returned {resp.status_code}",
            )

        try:
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            return OncoKBError(query=query, error_kind="parse_error", detail=str(e)[:200])

        try:
            options = tuple(
                OncoKBTherapeuticOption(
                    level=str(o.get("level", "?")),
                    drugs=tuple(o.get("drugs", [])),
                    description=o.get("description"),
                    pmids=tuple(str(p) for p in o.get("pmids", [])),
                    fda_approved=bool(o.get("fda_approved", False)),
                    fda_approval_year=o.get("fda_approval_year"),
                )
                for o in data.get("therapeutic_options", [])
            )
            return OncoKBResult(
                query=query,
                oncokb_url=data.get("oncokb_url", ""),
                therapeutic_options=options,
                cached=bool(data.get("cached", False)),
                oncokb_data_version=data.get("oncokb_data_version"),
            )
        except Exception as e:  # noqa: BLE001
            return OncoKBError(query=query, error_kind="parse_error", detail=str(e)[:200])

    def batch_lookup(
        self, queries: list[OncoKBQuery]
    ) -> list[OncoKBResult | OncoKBError]:
        # Sequential — for typical small batches (1-5 queries per Plan)
        # this is fine. If batches grow, swap to ThreadPoolExecutor with
        # bounded concurrency (semaphore=4 per safe-rollout v3 §3.1).
        return [self.lookup(q) for q in queries]


__all__ = [
    "OncoKBClient",
    "NullOncoKBClient",
    "StubOncoKBClient",
    "HttpxOncoKBClient",
]

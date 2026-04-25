"""Smoke + unit tests for the OncoKB proxy. Live calls are mocked.

Run from project root:
    cd services/oncokb_proxy
    pip install -r requirements.txt -r tests/requirements.txt
    pytest tests/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure scaffold mode for tests; live mode is integration-only.
os.environ.setdefault("ONCOKB_LIVE", "0")
os.environ.setdefault("ONCOKB_PROXY_CORS_ORIGINS", "https://openonco.org,http://localhost:8000")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402


client = TestClient(app)


def test_healthz_reports_scaffold_mode():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["live_mode"] is False
    assert body["token_configured"] is False  # no token set in test env
    assert "https://openonco.org" in body["allowed_origins"]


def test_lookup_scaffold_returns_empty_options_and_url():
    r = client.post(
        "/lookup",
        json={"gene": "BRAF", "variant": "V600E", "tumor_type": "MEL"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gene"] == "BRAF"
    assert body["variant"] == "V600E"
    assert body["oncokb_url"] == "https://www.oncokb.org/gene/BRAF/V600E"
    assert body["therapeutic_options"] == []
    assert body["cached"] is False


def test_lookup_caches_repeat_call():
    payload = {"gene": "EGFR", "variant": "L858R"}
    first = client.post("/lookup", json=payload).json()
    second = client.post("/lookup", json=payload).json()
    assert first["cached"] is False
    assert second["cached"] is True


def test_lookup_validates_input():
    r = client.post("/lookup", json={"gene": "", "variant": "V600E"})
    assert r.status_code == 422  # pydantic min_length violation


def test_cors_preflight_allows_openonco_origin():
    r = client.options(
        "/lookup",
        headers={
            "Origin": "https://openonco.org",
            "Access-Control-Request-Method": "POST",
        },
    )
    # FastAPI/Starlette auto-handles preflight; expect 200 with allow-origin
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://openonco.org"


def test_cors_preflight_allows_localhost_regex():
    r = client.options(
        "/lookup",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_lookup_normalizes_gene_to_uppercase():
    r = client.post("/lookup", json={"gene": "kras", "variant": "G12D"}).json()
    assert r["gene"] == "KRAS"
    assert r["oncokb_url"] == "https://www.oncokb.org/gene/KRAS/G12D"

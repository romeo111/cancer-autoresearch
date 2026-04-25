# OncoKB Proxy

Server-side proxy holding the OncoKB API token. Pyodide engine on
`openonco.org` calls this proxy instead of the OncoKB API directly,
because (a) the token is a secret that must not ship to the browser,
and (b) we want a 7-day in-memory LRU cache to respect rate limits.

**Status:** Phase 10 scaffold — not deployed. Tests pass in scaffold
mode (LIVE_MODE=0), live OncoKB call is implemented but un-exercised
until legal review of OncoKB Academic Terms vs the proxy architecture
clears (see `knowledge_base/hosted/content/sources/src_oncokb.yaml`
`legal_review.status: pending`).

## Run locally (scaffold mode)

```bash
cd services/oncokb_proxy
pip install -r requirements.txt -r tests/requirements.txt
pytest tests/
ONCOKB_LIVE=0 uvicorn app:app --reload --port 8080
curl -s http://localhost:8080/healthz | jq
curl -s -X POST http://localhost:8080/lookup \
  -H 'content-type: application/json' \
  -d '{"gene":"BRAF","variant":"V600E","tumor_type":"MEL"}' | jq
```

In scaffold mode, `/lookup` returns an empty `therapeutic_options` list
plus the canonical OncoKB URL — enough to wire the front-end render
without burning OncoKB API quota.

## Deploy to Cloud Run (when legal clears)

```bash
# 1. Store the OncoKB token in Secret Manager
echo -n "$ONCOKB_API_TOKEN" | gcloud secrets create oncokb-token --data-file=-

# 2. Deploy from source. Cloud Run builds from the Dockerfile.
gcloud run deploy oncokb-proxy \
  --source . \
  --region europe-west1 \
  --no-allow-unauthenticated \
  --set-env-vars=ONCOKB_LIVE=1,ONCOKB_PROXY_CORS_ORIGINS=https://openonco.org \
  --set-secrets=ONCOKB_API_TOKEN=oncokb-token:latest
```

`--no-allow-unauthenticated` keeps the service IAM-protected. The
`openonco.org` site calls it via service-account-signed URL or via
public allow + Cloudflare-WAF rule (decision deferred).

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `ONCOKB_API_BASE` | `https://www.oncokb.org/api/v1` | API root |
| `ONCOKB_API_TOKEN` | unset | Secret. Required when `ONCOKB_LIVE=1`. |
| `ONCOKB_LIVE` | `0` | `1` = real OncoKB calls; `0` = scaffold-mode stub. |
| `ONCOKB_CACHE_TTL_SECONDS` | `604800` | 7 days |
| `ONCOKB_CACHE_MAX_ENTRIES` | `4096` | LRU bound |
| `ONCOKB_PROXY_CORS_ORIGINS` | `https://openonco.org,http://localhost:8000,http://localhost:3000` | Comma-separated. Localhost any-port is also matched via regex. |

## Out of scope for this scaffold

- Render-side integration in `render_plan_html` (separate Phase).
- Production deployment / IAM (deferred until legal review).
- VUS / structural-variant lookups (CHARTER §8.3 + scope note in `src_oncokb.yaml`).
- Persistent cache (Redis/Memcached). Current LRU is per-instance, in-memory.

# Cloud Run-ready container for the OncoKB proxy.
#
# Deploy:
#   gcloud run deploy oncokb-proxy \
#     --source services/oncokb_proxy \
#     --region europe-west1 \
#     --no-allow-unauthenticated  # keep IAM-protected; openonco.org calls via signed URL or service account
#     --set-env-vars=ONCOKB_LIVE=1,ONCOKB_PROXY_CORS_ORIGINS=https://openonco.org
#     --set-secrets=ONCOKB_API_TOKEN=oncokb-token:latest
#
# Secret rotation: Secret Manager → version bump → no redeploy needed.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

# Cloud Run sends requests to PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT} --workers 1

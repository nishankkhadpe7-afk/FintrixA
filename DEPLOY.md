# Deploying Fintrix (Backend → Railway, Frontend → Vercel)

This file lists the recommended steps and required environment variables to deploy the Fintrix project.

## Overview

- Backend: Railway (or Docker on any host)
- Frontend: Vercel (Next.js)

## Required environment variables (set on both platforms where applicable)

- `DATABASE_URL` — Supabase Postgres connection string
- `FINTRIX_SECRET_KEY` — application secret
- `MISTRAL_API_KEY` — LLM provider key (or other provider key)
- `NEWS_API_KEY` — newsdata API key
- `ALLOWED_ORIGINS` — comma-separated allowed origins for CORS
- `ENABLE_NEWS_SCHEDULER` — `true` only on one instance (scheduler host)
- Optional: `SENTRY_DSN`, `RAILWAY_API_KEY`, `VERCEL_TOKEN`, `VECTOR_STORAGE_URL`

## Backend (Railway) — quick steps

1. Create a new Railway project and connect it to the repository (GitHub integration).
2. Add the required environment variables in Railway (see list above).
3. Configure Railway to run migrations after deploy. Two options:
   - CI (recommended): add a GitHub Actions workflow that runs `alembic upgrade head` before deploy (see `.github/workflows/ci-deploy.yml`).
   - Startup: use an `entrypoint` or container `CMD` that runs `alembic upgrade head` on boot.
4. Ensure the vector store (FAISS index files) are available in production:
   - Preferred: store index files in object storage (S3) and mount them into the service, or
   - Rebuild: run ingestion job on first boot (scripts/ingest_sebi_documents.py). This can be a one-time Railway job.
5. Set `ENABLE_NEWS_SCHEDULER=true` on a single instance (or run a separate Railway service for scheduled tasks).

## Frontend (Vercel) — quick steps

1. Import the repository into Vercel (or configure GitHub integration).
2. Set environment variables in Vercel:
   - `NEXT_PUBLIC_API_URL` → `https://<your-backend-host>` (if not using same-domain proxy)
   - `FINTRIX_SECRET_KEY` (only if used in SSR/build), etc.
3. If you prefer same-origin `/api` proxying, configure Vercel rewrites to forward `/api` to the Railway backend.

## CI (recommended)

- Add a GitHub Actions workflow that runs:
  1. Install Python deps (Backend/fintrix-api/requirements.txt)
  2. Run `alembic upgrade head` with `DATABASE_URL` from secrets
  3. Run smoke tests (`test_endpoints.py`, `test_full_integration.py`) — fail on non-zero exit
  4. Let Vercel/Railway handle deployments via their GitHub integrations

## Observability

- Add Sentry or similar for error tracking.
- Export metrics (request latency, LLM call errors, RAG index health) to Prometheus/Datadog.

## Security & Cost

- Ensure LLM keys are rotated and limited by role.
- Monitor LLM usage/costs in production; add rate-limits or request-sampling if needed.

## Notes

- This repo already contains `scripts/ingest_sebi_documents.py` and `alembic` migrations. Use the CI or startup migration approach to ensure the DB schema is applied before serving traffic.

If you want, I can create the GitHub Actions workflow file and optionally an entrypoint script to run migrations and optionally ingest the vector-store on first boot.

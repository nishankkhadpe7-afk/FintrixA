# DevOps Notes

## Deployment split

- Deploy `Frontend/fintrix-web` as the Next.js frontend
- Deploy `Backend/fintrix-api` as the FastAPI backend
- Keep `Database/s92.db` for local development only

## Required backend environment variables

- `DATABASE_URL`
- `NEWS_API_KEY`
- `MISTRAL_API_KEY`
- `FINTRIX_SECRET_KEY`
- `ALLOWED_ORIGINS` (comma-separated, defaults to `*`)
- `ENABLE_NEWS_SCHEDULER` (`1` or `0`)

## Suggested services

- Frontend: Vercel
- Backend: Render / Railway / VPS

## Before production

- Set `NEXT_PUBLIC_API_URL` on the frontend service to your backend URL
- Move sensitive secrets out of local `.env` and into your deployment platform environment settings
- Use a managed production database via `DATABASE_URL`
- Point build and root-directory settings at the restructured app folders instead of the workspace root

## Suggested service roots

- Vercel root directory: `Frontend/fintrix-web`
- Render or Railway root directory: `Backend/fintrix-api`

## Deployment baseline now included

- Backend deployment image: `Backend/fintrix-api/Dockerfile`
- CI workflow (active app paths): `.github/workflows/ci.yml`
- DB migrations: `Backend/fintrix-api/alembic`
- Production env templates:
  - `Backend/fintrix-api/.env.production.example`
  - `Frontend/fintrix-web/.env.production.example`
- Monitoring and backup guide: `DevOps/RUNBOOK.md`

## Production migration process

1. Set `ENABLE_AUTO_SCHEMA_CREATE=0` on backend.
2. Run `alembic upgrade head` from `Backend/fintrix-api`.
3. Start backend service.
4. Deploy frontend with `NEXT_PUBLIC_API_URL` set.

## CORS examples

- Single origin:
  - `ALLOWED_ORIGINS=https://fintrix.app`
- Multiple origins:
  - `ALLOWED_ORIGINS=https://fintrix.app,https://www.fintrix.app,https://staging.fintrix.app`

## SEBI document ingestion

If you already have reviewed SEBI regulations, master circulars, or circulars in the legacy document corpus, you can ingest them into the active compliance table with:

```powershell
cd Backend/fintrix-api
python scripts/ingest_sebi_documents.py --dry-run
python scripts/ingest_sebi_documents.py
```

By default, the script reads:

- `Legacy/project/documents/sebi/manifest.json`
- `Legacy/project/documents/sebi/**`

Set `MISTRAL_API_KEY` to enable extraction. Without it, the script safely skips rule extraction.

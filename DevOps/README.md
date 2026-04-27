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
- Database: Supabase Postgres

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

## Supabase Postgres setup

1. Create a new project in Supabase.
2. Open `Project Settings -> Database`.
3. The password in the connection string is the database password you created with the project.
4. If you forgot it, reset it in `Project Settings -> Database Settings`.
5. Copy the connection string and use the pooler form for Railway, not local SQLite.
6. Set the backend `DATABASE_URL` like this:
   - `postgresql+psycopg2://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require`
7. Set `APP_ENV=production`.
8. Set a strong `FINTRIX_SECRET_KEY`.
9. Set `ALLOWED_ORIGINS` to your frontend domain or domains.
10. Set `ENABLE_AUTO_SCHEMA_CREATE=0`.
11. Set `ENABLE_RULE_SEED_ON_STARTUP=0`.
12. Set `ENABLE_NEWS_SCHEDULER=0` unless you explicitly want one backend instance doing scheduled fetches.
13. Run `alembic upgrade head` against the Supabase database before first production traffic.
14. If you want starter compliance rules in production, seed them intentionally with a one-time script run instead of relying on startup auto-seeding.

## Migrating existing SQLite data

If you want to move your existing local data from `Database/s92.db` into Supabase:

1. Run migrations first:
   - `cd Backend/fintrix-api`
   - `python -m alembic upgrade head`
2. Run the one-time migration script:
   - `TARGET_DATABASE_URL="your-supabase-url"`
   - `python scripts/migrate_sqlite_to_postgres.py`
3. If the target already contains data and you intentionally want to replace it:
   - set `TRUNCATE_TARGET=1`

## Backend production env file

Use `Backend/fintrix-api/.env.production.example` as the template for your backend deployment variables.

## Frontend production env file

Use `Frontend/fintrix-web/.env.production.example` as the template for your frontend deployment variables.

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

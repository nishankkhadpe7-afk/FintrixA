# FinTrix Operations Runbook

## 1) Health-check monitoring

### Backend

- Health URL: `/api/health`
- Expected response: `{"status":"ok"}`
- Alert if unavailable for 2 consecutive checks
- Suggested interval: 60 seconds

### Frontend

- Health URL: `/` (HTTP 200)
- Alert on 5xx spikes or response time above threshold

### Synthetic checks

- Query backend `/api/health`
- Query frontend `/`
- Optionally query `/api/news` and `/api/blog/posts`

## 2) Database migration process (production)

Always run migrations before rolling out app code that depends on schema updates.

### Command

- `cd Backend/fintrix-api`
- `alembic upgrade head`

### Rollback

- `alembic downgrade -1`

### Deployment order

1. Backup database
2. Run `alembic upgrade head`
3. Deploy backend
4. Deploy frontend
5. Run smoke checks

## 3) Backup strategy

### PostgreSQL (recommended in production)

- Daily full backup
- Keep at least 7 daily + 4 weekly snapshots
- Example command:
  - `pg_dump "$DATABASE_URL" -Fc -f fintrix_$(date +%Y%m%d_%H%M%S).dump`

### SQLite (development only)

- File location: `Database/s92.db`
- Backup by file copy when app is stopped

## 4) Restore procedure

### PostgreSQL

- `pg_restore --clean --if-exists -d "$DATABASE_URL" fintrix_backup.dump`
- Run `alembic upgrade head`

### SQLite

- Replace the database file with backup copy
- Start backend and run smoke checks

## 5) Incident checklist

1. Confirm backend health (`/api/health`)
2. Check deployment logs (backend and frontend)
3. Check database connectivity and recent migration state
4. Validate `ALLOWED_ORIGINS` and frontend `NEXT_PUBLIC_API_URL`
5. Run smoke tests for core routes (`/api/health`, `/api/news`, `/api/blog/posts`)

## 6) Supabase-specific deployment checklist

1. Confirm `DATABASE_URL` uses the Postgres driver form:
   - `postgresql+psycopg2://...?...sslmode=require`
2. Confirm `APP_ENV=production`.
3. Confirm `FINTRIX_SECRET_KEY` is not the development fallback.
4. Confirm `ENABLE_AUTO_SCHEMA_CREATE=0`.
5. Confirm `ENABLE_RULE_SEED_ON_STARTUP=0`.
6. Confirm `ALLOWED_ORIGINS` exactly matches the deployed frontend origins.
7. Run `alembic upgrade head`.
8. Verify `/api/health` after deploy.

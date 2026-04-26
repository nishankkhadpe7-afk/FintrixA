# FinTrix Workspace

This repo is organized by responsibility so the active apps, database assets, deployment notes, and legacy experiments are easy to find and deploy separately.

## Workspace layout

- `Frontend/fintrix-web`
  - Main Next.js application
- `Backend/fintrix-api`
  - FastAPI backend, rules engine, AI services, docs, and tests
- `Database/s92.db`
  - Local SQLite database used for development
- `DevOps`
  - Deployment notes and environment guidance
- `Legacy/project`
  - Older experimental code kept outside the active app paths
- `SEBI_INTEGRATION_GUIDE.md`
  - Complete guide to the 124-rule SEBI compliance engine

## Local development

### Backend

```powershell
cd .\Backend\fintrix-api
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd .\Frontend\fintrix-web
Copy-Item .env.example .env.local
npm install
npm run dev
```

## SEBI Compliance Rules

FinTrix includes **124 SEBI compliance rules** extracted from 30 official regulatory documents (master circulars, regulations, circulars). Rules are available immediately in the evaluation engine with no additional setup required.

**Quick start**: See [SEBI_INTEGRATION_GUIDE.md](SEBI_INTEGRATION_GUIDE.md) for:

- Using mock mode to test with synthetic rules
- Activating Mistral AI for intelligent rule extraction
- Integrating with the evaluation simulator
- Performance and troubleshooting notes

## Deployment notes

- Deploy `Frontend/fintrix-web` and `Backend/fintrix-api` as separate services.
- Set `NEXT_PUBLIC_API_URL` in the frontend to your deployed backend URL.
- Set backend secrets on the backend service instead of relying on `backend/.env`.
- Set `DATABASE_URL` on Railway to your production database connection string.

## Production migration quick start

```powershell
cd .\Backend\fintrix-api
alembic upgrade head
```

See `DevOps/README.md` and `DevOps/RUNBOOK.md` for full deployment, CORS, health-check, and backup guidance.

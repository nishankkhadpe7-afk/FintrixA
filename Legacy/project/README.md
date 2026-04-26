# RegTech Evaluation Simulator

This project is a finance-focused regulatory evaluation simulator with three core layers:

- a React frontend for dashboard, circulars, rules, traceability, and evaluation
- a FastAPI backend for ingestion, rule retrieval, simulation, and system endpoints
- a PostgreSQL-backed rule engine and document-ingestion pipeline

It supports multi-domain simulation across:

- Lending
- Forex
- Trading
- Bonds

## What It Does

The system collects official regulator documents, extracts candidate rules, stores raw source text, persists validated executable rules, and evaluates user scenarios against the active rule set with reasoning traces.

Current source workflows:

- RBI: automated RSS-driven ingestion
- SEBI: reviewed local-document ingestion with official URL validation

## Project Structure

- [api](C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\api): FastAPI app, routers, schemas, services
- [frontend](C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\frontend): React + Vite dashboard UI
- [ingestion](C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\ingestion): RSS fetchers, scraper, manual ingestion, raw storage, persistence helpers
- [seed_data](C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\seed_data): starter benchmark rules and scenarios
- [tests](C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\tests): baseline validation tests

## Run Locally

Backend:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
uvicorn api.main:app --reload --port 8001
```

Frontend:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project\frontend"
npm run dev
```

Frontend URL:

- [http://localhost:5173](http://localhost:5173)

Backend docs:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

## Ingestion Commands

RBI automated ingestion:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python run_ingestion.py
```

SEBI batch reviewed-document ingestion:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python batch_ingest_sebi_documents.py
```

Single SEBI document:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python ingest_sebi_document.py "documents/sebi/your_file.pdf" "Your Document Title" "https://www.sebi.gov.in/official-page"
```

## Benchmark Commands

Seed benchmark rules:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python seed_benchmark_data.py
```

Run benchmark suite:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python run_benchmark_suite.py
```

## Tests

Run baseline tests:

```powershell
cd "C:\Users\Nishank\Desktop\Mini-Project\1-Mini-Project-A\Data\rag_ingestion\project"
python -m unittest discover -s tests
```

## Security / Source Policy

The ingestion workflow now validates official regulator sources before scraping or storing documents.

Allowed source domains:

- `rbi.org.in`
- `www.rbi.org.in`
- `sebi.gov.in`
- `www.sebi.gov.in`

This is enforced for:

- automated RBI URL ingestion
- manual SEBI `official_url` ingestion
- raw HTTP document storage

## Optional API Auth

API auth support is available but disabled by default.

Environment variables:

- `API_AUTH_ENABLED=true`
- `API_KEY=your-secret-key`

When enabled, non-system endpoints require the `x-api-key` header.

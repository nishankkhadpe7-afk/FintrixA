# Fintrix Start Script
# This script starts both the backend and frontend services.

# 1. Start Backend
Write-Host "Starting Backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd Backend/fintrix-api; .\venv\Scripts\activate; python -m uvicorn backend.main:app --reload --port 8000"

# 2. Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd Frontend/fintrix-web; npm run dev"

Write-Host "Services are starting in separate windows." -ForegroundColor Cyan
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:3000"

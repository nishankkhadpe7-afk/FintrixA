@echo off
REM Start backend server on port 8001
REM This script ensures the backend always runs on the correct port

cd /d "%~dp0"

echo ====================================
echo Starting RegTech Backend Server
echo Port: 8001
echo ====================================
echo.

uvicorn api.main:app --reload --port 8001

pause

@echo off
REM Start frontend server (static HTML)
REM Port: 3000

cd /d "%~dp0frontend"

echo ====================================
echo Starting RegTech Frontend Server
echo Port: 3000
echo ====================================
echo.

REM Check if Python is available for simple HTTP server
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using Python HTTP server...
    python -m http.server 3000
) else (
    echo Python not found. Please install Python or use another HTTP server.
    echo Alternatively, open index.html directly in a browser.
    pause
)

@echo off
setlocal
cd /d "%~dp0"

if /i "%~1"=="--backend" goto backend
if /i "%~1"=="--frontend" goto frontend

if not exist ".venv\Scripts\python.exe" (
    echo Python environment is missing. Follow the setup steps in README.md first.
    goto failed
)

where node.exe >nul 2>&1
if errorlevel 1 (
    echo Node.js is missing from PATH. Install Node.js 20.9 or newer.
    goto failed
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo npm is missing from PATH. Reinstall Node.js, then reopen this launcher.
    goto failed
)

if not exist "frontend\node_modules\.bin\next.cmd" (
    echo Frontend dependencies are missing. Run npm ci in the frontend folder first.
    goto failed
)

".venv\Scripts\python.exe" -c "import app.main, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Backend dependencies or configuration are invalid. Follow README.md setup steps.
    goto failed
)

if /i "%~1"=="--check" (
    echo Startup prerequisites are available.
    exit /b 0
)

echo Starting Chakravyuh in two terminal windows...
echo Workbench: http://127.0.0.1:3000
echo API docs:  http://127.0.0.1:8001/docs
echo Use Ctrl+C in each service window to stop it.
echo If either port is already in use, stop the previous instance first.

start "Chakravyuh Backend" "%ComSpec%" /k ""%~f0" --backend"
start "Chakravyuh Frontend" "%ComSpec%" /k ""%~f0" --frontend"
exit /b 0

:backend
title Chakravyuh Backend
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --loop asyncio
exit /b %errorlevel%

:frontend
title Chakravyuh Frontend
cd /d "%~dp0frontend"
call npm.cmd run dev
exit /b %errorlevel%

:failed
echo.
if /i not "%~1"=="--check" pause
exit /b 1

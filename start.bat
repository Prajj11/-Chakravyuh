@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "NEXT_TELEMETRY_DISABLED=1"
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8001"
set "CHAKRAVYUH_FRONTEND_ORIGIN=http://127.0.0.1:3000"

:: Load connector environment if present
if exist "%~dp0.runtime\connector-env.bat" (
    call "%~dp0.runtime\connector-env.bat"
)

:: Ensure live-feeds configuration exists
if not exist "%~dp0live-feeds.local.json" (
    if exist "%~dp0live-feeds.example.json" (
        copy /y "%~dp0live-feeds.example.json" "%~dp0live-feeds.local.json" >nul
    )
)
if exist "%~dp0live-feeds.local.json" (
    set "CHAKRAVYUH_LIVE_FEEDS_FILE=%~dp0live-feeds.local.json"
)

:: Sub-service triggers
if /i "%~1"=="--backend" goto backend
if /i "%~1"=="--frontend" goto frontend
if /i "%~1"=="--setup" goto setup_only
if /i "%~1"=="--check" goto check_only

call :check_tools
if errorlevel 1 goto failed

:: Check existing setup or prepare
if not exist ".venv\Scripts\python.exe" goto prepare
if not exist "frontend\node_modules\next\dist\bin\next" goto prepare
".venv\Scripts\python.exe" scripts/dependency_stamp.py >nul 2>&1
if errorlevel 1 goto prepare
".venv\Scripts\python.exe" -c "import app.config, fastapi, uvicorn" >nul 2>&1
if errorlevel 1 goto prepare
goto run_services

:prepare
call :setup
if errorlevel 1 goto failed

:run_services
:: Verify ports 8001 and 3000 are available
".venv\Scripts\python.exe" scripts/open_workbench.py --ports-free
if errorlevel 1 goto failed

echo ============================================================
echo   Chakravyuh - Integrated Launcher
echo   Frontend + Backend + Live Collection
echo ============================================================
echo   Workbench:        http://127.0.0.1:3000
echo   API & Docs:       http://127.0.0.1:8001/docs
echo   Live Feeds:       %CHAKRAVYUH_LIVE_FEEDS_FILE%
echo ============================================================
echo Starting Backend and Frontend service windows...
echo Press Ctrl+C in each service window to stop it.
echo.

start "Chakravyuh Backend (API + Live Feeds)" "%ComSpec%" /k ""%~f0" --backend"
start "Chakravyuh Frontend" "%ComSpec%" /k ""%~f0" --frontend"

echo Waiting for services to become ready before opening browser...
".venv\Scripts\python.exe" scripts/open_workbench.py
if errorlevel 1 goto failed
exit /b 0

:backend
title Chakravyuh Backend & Live Feeds
cd /d "%~dp0"
echo ============================================================
echo   Chakravyuh Backend & Live Feed Collector
echo ============================================================
echo   API Docs:   http://127.0.0.1:8001/docs
echo   Live Feeds: %CHAKRAVYUH_LIVE_FEEDS_FILE%
echo ============================================================
".venv\Scripts\python.exe" scripts/open_workbench.py --ports-free 8001
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --loop asyncio
exit /b %errorlevel%

:frontend
title Chakravyuh Frontend
cd /d "%~dp0frontend"
echo ============================================================
echo   Chakravyuh Frontend Workbench
echo ============================================================
echo   Workbench:  http://127.0.0.1:3000
echo   Backend:    %NEXT_PUBLIC_API_URL%
echo ============================================================
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\open_workbench.py" --ports-free 3000
if errorlevel 1 goto failed
node node_modules\next\dist\bin\next dev --hostname 127.0.0.1 --port 3000
exit /b %errorlevel%

:check_only
call :check_tools
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment is missing. Run start.bat --setup
    goto failed
)
if not exist "frontend\node_modules\next\dist\bin\next" (
    echo Frontend dependencies are missing. Run start.bat --setup
    goto failed
)
".venv\Scripts\python.exe" scripts/dependency_stamp.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 'Python 3.11+ is required.')"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import app.config, fastapi, uvicorn; from importlib.metadata import version; print('Backend ready: ' + version('chakravyuh-backend'))"
if errorlevel 1 goto failed
echo Prerequisites verified successfully.
exit /b 0

:setup_only
call :check_tools
if errorlevel 1 goto failed
call :setup
exit /b %errorlevel%

:check_tools
where node.exe >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js 20.9+ with npm is required.
    exit /b 1
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo Error: npm.cmd is missing from PATH.
    exit /b 1
)
node -e "const [major, minor] = process.versions.node.split('.').map(Number); if (major < 20 || (major === 20 && minor < 9)) { console.error('Node.js 20.9+ is required.'); process.exit(1); }"
exit /b %errorlevel%

:setup
echo Setting up Python virtual environment and dependencies...
if exist ".venv\Scripts\python.exe" goto install_dependencies
where py.exe >nul 2>&1
if errorlevel 1 goto python_fallback
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv .venv
    if not errorlevel 1 goto install_dependencies
)
py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.13 -m venv .venv
    if not errorlevel 1 goto install_dependencies
)
goto python_fallback

:python_fallback
where python.exe >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.11+ is required.
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 'Python 3.11+ is required.')"
if errorlevel 1 exit /b 1
python -m venv .venv
if errorlevel 1 exit /b 1

:install_dependencies
echo Installing backend Python dependencies...
".venv\Scripts\python.exe" -m pip install -c backend/requirements.lock -e "./backend[dev]"
if errorlevel 1 exit /b 1
echo Installing frontend dependencies...
pushd frontend
call npm.cmd ci --no-audit --no-fund
set "INSTALL_STATUS=%errorlevel%"
popd
if not "%INSTALL_STATUS%"=="0" exit /b %INSTALL_STATUS%
".venv\Scripts\python.exe" scripts/dependency_stamp.py --write
echo Setup complete.
exit /b 0

:failed
echo.
echo Startup failed. Check the error messages above.
if "%~1"=="" pause
exit /b 1

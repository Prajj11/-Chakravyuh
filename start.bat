@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "NEXT_TELEMETRY_DISABLED=1"

if /i "%~1"=="--backend" goto backend
if /i "%~1"=="--frontend" goto frontend
if /i "%~1"=="--setup" goto setup_only

call :check_tools
if errorlevel 1 goto failed
if /i "%~1"=="--check" goto check
if not "%~1"=="" (
    echo Usage: start.bat [--setup^|--check]
    exit /b 2
)

if not exist ".venv\Scripts\python.exe" goto prepare
if not exist "frontend\node_modules\next\dist\bin\next" goto prepare
".venv\Scripts\python.exe" scripts/dependency_stamp.py >nul 2>&1
if errorlevel 1 goto prepare
".venv\Scripts\python.exe" -c "import app.config, fastapi, uvicorn" >nul 2>&1
if errorlevel 1 goto prepare
goto check

:prepare
call :setup
if errorlevel 1 goto failed

:check
if not exist ".venv\Scripts\python.exe" (
    echo Python environment is missing. Run start.bat --setup.
    goto failed
)
if not exist "frontend\node_modules\next\dist\bin\next" (
    echo Frontend dependencies are missing. Run start.bat --setup.
    goto failed
)
".venv\Scripts\python.exe" scripts/dependency_stamp.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 'Python 3.11+ is required.')"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import app.config, fastapi, uvicorn; from importlib.metadata import version; print('Backend ready: ' + version('chakravyuh-backend'))"
if errorlevel 1 (
    echo Backend dependencies or configuration are invalid. Run start.bat --setup.
    goto failed
)
if /i "%~1"=="--check" (
    echo Startup prerequisites are available.
    exit /b 0
)

".venv\Scripts\python.exe" scripts/open_workbench.py --ports-free
if errorlevel 1 goto failed

echo Starting Chakravyuh in two terminal windows...
echo Workbench: http://127.0.0.1:3000
echo API docs:  http://127.0.0.1:8001/docs
echo Use Ctrl+C in each service window to stop it.
echo If either port is already in use, stop the previous instance first.

start "Chakravyuh Backend" "%ComSpec%" /k ""%~f0" --backend"
start "Chakravyuh Frontend" "%ComSpec%" /k ""%~f0" --frontend"
echo Waiting for both services before opening the workbench...
".venv\Scripts\python.exe" scripts/open_workbench.py
if errorlevel 1 goto failed
exit /b 0

:backend
title Chakravyuh Backend
".venv\Scripts\python.exe" scripts/open_workbench.py --ports-free 8001
if errorlevel 1 goto failed
echo Backend API: http://127.0.0.1:8001/docs
echo Open the app at http://127.0.0.1:3000
echo Both services must be running. Use start.bat or also run start-frontend.bat.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --loop asyncio
exit /b %errorlevel%

:frontend
title Chakravyuh Frontend
".venv\Scripts\python.exe" scripts/open_workbench.py --ports-free 3000
if errorlevel 1 goto failed
echo Workbench: http://127.0.0.1:3000
echo Keep the backend running on port 8001. Use start.bat or also run start-backend.bat.
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8001"
cd /d "%~dp0frontend"
node node_modules\next\dist\bin\next dev --hostname 127.0.0.1 --port 3000
exit /b %errorlevel%

:setup_only
call :check_tools
if errorlevel 1 goto failed
call :setup
exit /b %errorlevel%

:check_tools
where node.exe >nul 2>&1
if errorlevel 1 (
    echo Install Node.js 24 with npm, then reopen this launcher.
    exit /b 1
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo npm is missing from PATH. Reinstall Node.js, then reopen this launcher.
    exit /b 1
)
node -e "const [major, minor] = process.versions.node.split('.').map(Number); if (major < 20 || (major === 20 && minor < 9)) { console.error('Node.js 20.9+ is required; Node.js 24 is recommended.'); process.exit(1); }"
exit /b %errorlevel%

:setup
if exist ".venv\Scripts\python.exe" goto install_dependencies
if exist ".venv\bin\python" (
    echo This checkout has a Linux environment. Use scripts/dev.sh there or a separate Windows checkout.
    exit /b 1
)
where py.exe >nul 2>&1
if errorlevel 1 goto python_fallback
py -3.12 -c "import sys" >nul 2>&1
if errorlevel 1 goto python_fallback
py -3.12 -m venv .venv
if errorlevel 1 exit /b 1
goto install_dependencies

:python_fallback
where python.exe >nul 2>&1
if errorlevel 1 (
    echo Install Python 3.12 and add it to PATH, then reopen this launcher.
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 'Python 3.11+ is required; Python 3.12 is recommended.')"
if errorlevel 1 exit /b 1
python -m venv .venv
if errorlevel 1 exit /b 1

:install_dependencies
".venv\Scripts\python.exe" -m pip install -c backend/requirements.lock -e "./backend[dev]"
if errorlevel 1 exit /b 1
pushd frontend
call npm.cmd ci --no-audit --no-fund
set "INSTALL_STATUS=%errorlevel%"
popd
if not "%INSTALL_STATUS%"=="0" exit /b %INSTALL_STATUS%
".venv\Scripts\python.exe" scripts/dependency_stamp.py --write
exit /b %errorlevel%

:failed
echo.
if "%~1"=="" pause
exit /b 1

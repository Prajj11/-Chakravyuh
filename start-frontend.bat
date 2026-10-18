@echo off
setlocal
cd /d "%~dp0"

call "%~dp0start.bat" --check
if errorlevel 1 goto failed
if /i "%~1"=="--check" exit /b 0

call "%~dp0start.bat" --frontend
set "SERVICE_STATUS=%errorlevel%"
if not "%SERVICE_STATUS%"=="0" pause
exit /b %SERVICE_STATUS%

:failed
echo Run setup.bat to install or repair dependencies, then try again.
if "%~1"=="" pause
exit /b 1

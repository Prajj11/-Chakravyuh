@echo off
setlocal
cd /d "%~dp0"

call "%~dp0start.bat" --setup
set "SETUP_STATUS=%errorlevel%"
if "%SETUP_STATUS%"=="0" echo Setup completed. Double-click start.bat to launch Chakravyuh.
if /i not "%~1"=="--no-pause" pause
exit /b %SETUP_STATUS%

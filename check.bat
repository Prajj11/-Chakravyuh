@echo off
setlocal
cd /d "%~dp0"

call "%~dp0start.bat" --check
set "CHECK_STATUS=%errorlevel%"
if /i not "%~1"=="--no-pause" pause
exit /b %CHECK_STATUS%

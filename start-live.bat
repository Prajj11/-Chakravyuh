@echo off
setlocal
cd /d "%~dp0"
if not exist "live-feeds.local.json" (
  copy /y "live-feeds.example.json" "live-feeds.local.json" >nul
)
set "CHAKRAVYUH_LIVE_FEEDS_FILE=%~dp0live-feeds.local.json"
echo Starting public API polling using live-feeds.local.json
echo Edit that file to choose topics, platforms and polling intervals.
call "%~dp0start.bat" %*
exit /b %errorlevel%

@echo off
rem Compatibility entry point; the integrated launcher loads configured public feeds.
call "%~dp0start.bat" %*
exit /b %errorlevel%

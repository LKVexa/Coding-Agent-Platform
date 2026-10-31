@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Platform.ps1" %*
if not "%~1"=="" exit /b %errorlevel%
pause

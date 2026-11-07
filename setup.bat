@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed. Read the message above, then try setup.bat again.
)
pause

@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0share.ps1"
if errorlevel 1 (
    echo.
    echo Couldn't create the share zip. Read the message above.
)
pause

@echo off
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%.venv\Scripts\pythonw.exe" (
    echo Run setup.bat first to install the app.
    pause
    exit /b 1
)
start "Pico Chest Counter" "%APP_DIR%.venv\Scripts\pythonw.exe" "%APP_DIR%pico_chest_counter.py"

@echo off
set "APP_EXE=%LOCALAPPDATA%\Programs\Delta Chest Counter\DeltaChestCounter.exe"
if not exist "%APP_EXE%" (
    echo Delta Chest Counter is not installed yet. Run setup.bat first.
    pause
    exit /b 1
)
start "" "%APP_EXE%"

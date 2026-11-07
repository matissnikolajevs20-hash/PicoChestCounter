$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $appDir ".venv"
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $python = $pythonCommand.Source
    } else {
        throw "Python 3.12 was not found. Install it from python.org, then run setup.bat again."
    }
}

Write-Host "Creating the app's Python environment..."
if (-not (Test-Path (Join-Path $venvDir "Scripts\python.exe"))) {
    & $python -m venv $venvDir
}
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Write-Host "Installing speech recognition and microphone libraries..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $appDir "requirements.txt")

$modelDir = Join-Path $appDir "vosk-model-small-en-us-0.15"
if (-not (Test-Path $modelDir)) {
    $zipPath = Join-Path $env:TEMP "vosk-model-small-en-us-0.15.zip"
    $modelUrl = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    Write-Host "Downloading the offline English speech model..."
    Invoke-WebRequest -Uri $modelUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $appDir -Force
    Remove-Item $zipPath -Force
}

$pythonw = Join-Path $venvDir "Scripts\pythonw.exe"
$script = Join-Path $appDir "pico_chest_counter.py"
$shell = New-Object -ComObject WScript.Shell
$desktopShortcut = $shell.CreateShortcut(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Delta Chest Counter.lnk")
)
$desktopShortcut.TargetPath = $pythonw
$desktopShortcut.Arguments = "`"$script`""
$desktopShortcut.WorkingDirectory = $appDir
$desktopShortcut.Description = "Launch Delta Chest Counter"
$desktopShortcut.Save()

$startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "Delta Chest Counter"
New-Item -ItemType Directory -Path $startMenu -Force | Out-Null
$startShortcut = $shell.CreateShortcut(
    (Join-Path $startMenu "Delta Chest Counter.lnk")
)
$startShortcut.TargetPath = $pythonw
$startShortcut.Arguments = "`"$script`""
$startShortcut.WorkingDirectory = $appDir
$startShortcut.Description = "Launch Delta Chest Counter"
$startShortcut.Save()

Write-Host "Setup complete. Use the desktop or Start menu shortcut to launch the app."
Write-Host "Right-click the shortcut and choose Pin to taskbar for one-click access."

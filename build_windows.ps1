$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir = Join-Path $appDir "build"
$venvDir = Join-Path $appDir ".build-venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$innoCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)

if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.12 was not found. Install Python 3.12 and run this script again."
    }
    $python = $pythonCommand.Source
}

$iscc = $innoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 is required to build the installer. Install it from https://jrsoftware.org/isdl.php."
}

if (-not (Test-Path $venvPython)) {
    & $python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Could not create build environment." }
}

& $venvPython -m pip install -r (Join-Path $appDir "requirements.txt") -r (Join-Path $appDir "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install build dependencies." }

$modelDir = Join-Path $buildDir "vosk-model-small-en-us-0.15"
if (-not (Test-Path (Join-Path $modelDir "am\final.mdl"))) {
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    $modelZip = Join-Path $buildDir "vosk-model-small-en-us-0.15.zip"
    Invoke-WebRequest `
        -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" `
        -OutFile $modelZip
    Expand-Archive -Path $modelZip -DestinationPath $buildDir -Force
    Remove-Item -LiteralPath $modelZip -Force
}

$iconPath = Join-Path $buildDir "delta-chest-counter.ico"
& $venvPython (Join-Path $appDir "tools\create_icon.py") $iconPath
if ($LASTEXITCODE -ne 0) { throw "Could not generate the app icon." }

Push-Location $appDir
try {
    & $venvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "DeltaChestCounter" `
        --icon $iconPath `
        --add-data "$modelDir;vosk-model-small-en-us-0.15" `
        --hidden-import updater `
        --collect-all vosk `
        --collect-all sounddevice `
        pico_chest_counter.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    $version = (Get-Content (Join-Path $appDir "app_version.txt") -Raw).Trim()
    & $iscc "/DAppVersion=$version" (Join-Path $appDir "packaging\PicoChestCounter.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup could not build the installer." }
} finally {
    Pop-Location
}

Write-Host "Installer created: $(Join-Path $appDir 'dist\installer\PicoChestCounter-Setup.exe')"

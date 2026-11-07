$ErrorActionPreference = "Stop"
$repository = "matissnikolajevs20-hash/PicoChestCounter"
$apiUrl = "https://api.github.com/repos/$repository/releases/latest"
$headers = @{
    Accept = "application/vnd.github+json"
    "User-Agent" = "PicoChestCounter-Setup"
}

Write-Host "Finding the latest Delta Chest Counter installer..."
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 15
$asset = $release.assets | Where-Object {
    $_.name -eq "PicoChestCounter-Setup.exe"
} | Select-Object -First 1
if (-not $asset -or $asset.browser_download_url -notmatch '^https://') {
    throw "Release $($release.tag_name) does not contain PicoChestCounter-Setup.exe yet."
}

$installerPath = Join-Path $env:TEMP "PicoChestCounter-Setup.exe"
Write-Host "Downloading app installer..."
Invoke-WebRequest -Uri $asset.browser_download_url -Headers $headers -OutFile $installerPath -TimeoutSec 120

if ($asset.digest -match '^sha256:([0-9a-fA-F]{64})$') {
    $actualDigest = (Get-FileHash -Path $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualDigest -ne $Matches[1].ToLowerInvariant()) {
        Remove-Item -LiteralPath $installerPath -Force
        throw "The installer download failed its SHA-256 integrity check."
    }
}

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceCount = Join-Path $appDir "chest_count.json"
$dataDir = Join-Path $env:LOCALAPPDATA "DeltaChestCounter"
$targetCount = Join-Path $dataDir "chest_count.json"
if ((Test-Path -LiteralPath $sourceCount) -and -not (Test-Path -LiteralPath $targetCount)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Copy-Item -LiteralPath $sourceCount -Destination $targetCount
}

Write-Host "Starting the Delta Chest Counter installer..."
$process = Start-Process -FilePath $installerPath -Wait -PassThru
if ($process.ExitCode -ne 0) {
    throw "The installer exited with code $($process.ExitCode)."
}
Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
Write-Host "Setup finished. Launch Delta Chest Counter from the Start menu or Desktop."

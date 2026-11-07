$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $appDir "update-config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
if ($config.repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    $repository = Read-Host "GitHub repository for updates (owner/name)"
    if ($repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
        throw "Enter a valid public GitHub repository in owner/name format."
    }
    @{ repository = $repository } |
        ConvertTo-Json |
        Set-Content -Path $configPath -Encoding UTF8
}
$files = @(
    "pico_chest_counter.py",
    "updater.py",
    "app_version.txt",
    "update-config.json",
    "requirements.txt",
    "setup.bat",
    "setup.ps1",
    "run.bat",
    "share.bat",
    "share.ps1",
    "README.md"
) | ForEach-Object { Join-Path $appDir $_ }
$zipPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "PicoChestCounter.zip"

Compress-Archive -Path $files -DestinationPath $zipPath -Force
Write-Host "Bootstrap source zip created at: $zipPath"
Write-Host "New users should download PicoChestCounter-Setup.exe from the GitHub Releases page."

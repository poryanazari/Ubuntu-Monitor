param(
    [string]$Target = ""
)
$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
if (-not $Target) { $Target = Join-Path $ROOT "dist\ubuntu-monitor-server-offline-win" }
$WHEELS = Join-Path $ROOT "installer\wheels\server-win"

if (-not (Test-Path $WHEELS)) {
    throw "Missing wheels. Run installer\scripts\download_offline_packages.ps1 on an internet PC."
}

Write-Host "Installing server to $Target ..."
New-Item -ItemType Directory -Path $Target -Force | Out-Null
Copy-Item (Join-Path $ROOT "server") (Join-Path $Target "server") -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $Target "web\dist") -Force | Out-Null
Copy-Item (Join-Path $ROOT "web\dist\*") (Join-Path $Target "web\dist") -Recurse -Force
if (-not (Test-Path (Join-Path $Target "server\.env"))) {
    if (Test-Path (Join-Path $ROOT "server\.env.example")) {
        Copy-Item (Join-Path $ROOT "server\.env.example") (Join-Path $Target "server\.env.example") -Force
    }
}

python -m venv (Join-Path $Target "venv")
. (Join-Path $Target "venv\Scripts\Activate.ps1")
python -m pip install --no-index --find-links=$WHEELS -r (Join-Path $ROOT "server\requirements.txt")
python -m pip install --no-index --find-links=$WHEELS bcrypt

$startBat = @'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd server
set UBUNTU_MONITOR_DATA_DIR=%cd%
set UBUNTU_MONITOR_STATIC_DIR=%cd%\..\web\dist
echo Dashboard: http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
'@
Set-Content -Path (Join-Path $Target "start_server.bat") -Value $startBat -Encoding ASCII

Write-Host "Done. Copy folder to target machine and run start_server.bat"

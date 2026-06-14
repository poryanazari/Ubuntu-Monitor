$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$DIST = Join-Path $ROOT "dist"
$OUT = Join-Path $DIST "ubuntu-monitor-server-portable-windows"
$SERVER = Join-Path $ROOT "server"
$VENV = Join-Path $SERVER "venv"

Write-Host "=== Build Ubuntu Monitor Server (portable venv) ==="

if (-not (Test-Path (Join-Path $VENV "Scripts\python.exe"))) {
    throw "Missing server\venv. On build PC run: cd server; python -m venv venv; pip install -r requirements.txt"
}

$webIndex = Join-Path $ROOT "web\dist\index.html"
if (-not (Test-Path $webIndex)) {
    Write-Host "Building web UI ..."
    Push-Location (Join-Path $ROOT "web")
    npm run build
    Pop-Location
}

if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
New-Item -ItemType Directory -Path $OUT -Force | Out-Null

Write-Host "Copying application ..."
New-Item -ItemType Directory -Path (Join-Path $OUT "server") -Force | Out-Null
Copy-Item (Join-Path $SERVER "app") (Join-Path $OUT "server\app") -Recurse -Force
if (Test-Path (Join-Path $SERVER ".env.example")) {
    Copy-Item (Join-Path $SERVER ".env.example") (Join-Path $OUT "server\.env.example") -Force
}

Write-Host "Copying Python venv (offline-ready) ..."
Copy-Item $VENV (Join-Path $OUT "venv") -Recurse -Force

Write-Host "Copying web dashboard ..."
New-Item -ItemType Directory -Path (Join-Path $OUT "web\dist") -Force | Out-Null
Copy-Item (Join-Path $ROOT "web\dist\*") (Join-Path $OUT "web\dist") -Recurse -Force

$startBat = @'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd server
set UBUNTU_MONITOR_DATA_DIR=%cd%
set UBUNTU_MONITOR_STATIC_DIR=%cd%\..\web\dist
echo Ubuntu Monitor server
echo Dashboard: http://localhost:8000
echo Login: admin / admin123
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
'@
Set-Content -Path (Join-Path $OUT "start_server.bat") -Value $startBat -Encoding ASCII

$readme = @'
Ubuntu Monitor - portable server (Windows)

No internet required on this machine.
Requires nothing except this folder.

1. Copy .env.example to server\.env and edit (SECRET_KEY, Bale token, ...)
2. Run start_server.bat
3. Open http://SERVER_IP:8000

Data file: server\monitor.db (created on first run)
'@
Set-Content -Path (Join-Path $OUT "README.txt") -Value $readme -Encoding UTF8

Write-Host ""
Write-Host "Built: $OUT"
Write-Host "Zip this folder and copy to air-gapped servers."

$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$WHEELS = Join-Path $ROOT "installer\wheels"

Write-Host "=== Ubuntu Monitor: download offline packages (Windows) ==="
Write-Host "Root: $ROOT"

New-Item -ItemType Directory -Path $WHEELS -Force | Out-Null

Write-Host ""
Write-Host "[1/4] Server wheels (Windows) ..."
$serverWin = Join-Path $WHEELS "server-win"
New-Item -ItemType Directory -Path $serverWin -Force | Out-Null
python -m pip download -r (Join-Path $ROOT "server\requirements.txt") -d $serverWin
python -m pip download bcrypt -d $serverWin

Write-Host ""
Write-Host "[2/4] Agent wheels (Windows) ..."
$agentWin = Join-Path $WHEELS "agent-win"
New-Item -ItemType Directory -Path $agentWin -Force | Out-Null
python -m pip download -r (Join-Path $ROOT "agent\requirements.txt") -d $agentWin

Write-Host ""
Write-Host "[3/4] Build tools ..."
$buildWheels = Join-Path $WHEELS "build"
New-Item -ItemType Directory -Path $buildWheels -Force | Out-Null
python -m pip download -r (Join-Path $ROOT "installer\requirements-build.txt") -d $buildWheels

Write-Host ""
Write-Host "[4/4] Agent wheels (Linux x86_64) ..."
$agentLinux = Join-Path $WHEELS "agent-linux"
New-Item -ItemType Directory -Path $agentLinux -Force | Out-Null
try {
    python -m pip download -r (Join-Path $ROOT "agent\requirements.txt") -d $agentLinux --platform manylinux2014_x86_64 --python-version 311 --only-binary=:all:
} catch {
    Write-Host "Note: download Linux wheels on Ubuntu with download_offline_packages.sh if this step fails."
}

Write-Host ""
Write-Host "Done. Wheels saved under installer\wheels\"

$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$DIST = Join-Path $ROOT "dist"
$OUT = Join-Path $DIST "ubuntu-monitor-agent-portable-windows"
$AGENT = Join-Path $ROOT "agent"

Write-Host "=== Build Ubuntu Monitor Agent (portable venv, Windows) ==="

$venv = Join-Path $AGENT "venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    Write-Host "Creating agent venv and installing deps ..."
    python -m venv $venv
    & (Join-Path $venv "Scripts\python.exe") -m pip install -r (Join-Path $AGENT "requirements.txt")
}

if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
New-Item -ItemType Directory -Path $OUT -Force | Out-Null

Copy-Item $AGENT (Join-Path $OUT "agent") -Recurse -Force -Exclude venv,__pycache__
Copy-Item $venv (Join-Path $OUT "venv") -Recurse -Force
if (-not (Test-Path (Join-Path $OUT "agent\config.windows.yaml"))) {
    Copy-Item (Join-Path $OUT "agent\config.windows.yaml.example") (Join-Path $OUT "agent\config.windows.yaml") -Force
}

$startBat = @'
@echo off
cd /d "%~dp0agent"
call ..\venv\Scripts\activate.bat
python agent_windows.py -c config.windows.yaml
pause
'@
Set-Content -Path (Join-Path $OUT "start_agent.bat") -Value $startBat -Encoding ASCII

Write-Host "Built: $OUT"

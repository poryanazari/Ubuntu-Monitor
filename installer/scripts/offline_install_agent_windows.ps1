param(
    [string]$Target = ""
)
$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
if (-not $Target) { $Target = Join-Path $ROOT "dist\ubuntu-monitor-agent-offline-win" }
$WHEELS = Join-Path $ROOT "installer\wheels\agent-win"

if (-not (Test-Path $WHEELS)) {
    throw "Missing wheels. Run installer\scripts\download_offline_packages.ps1 on an internet PC."
}

Write-Host "Installing agent to $Target ..."
New-Item -ItemType Directory -Path $Target -Force | Out-Null
Copy-Item (Join-Path $ROOT "agent") (Join-Path $Target "agent") -Recurse -Force
if (-not (Test-Path (Join-Path $Target "agent\config.windows.yaml"))) {
    Copy-Item (Join-Path $Target "agent\config.windows.yaml.example") (Join-Path $Target "agent\config.windows.yaml") -Force
}

python -m venv (Join-Path $Target "venv")
. (Join-Path $Target "venv\Scripts\Activate.ps1")
python -m pip install --no-index --find-links=$WHEELS -r (Join-Path $ROOT "agent\requirements.txt")

$startBat = @'
@echo off
cd /d "%~dp0agent"
call ..\venv\Scripts\activate.bat
python agent_windows.py -c config.windows.yaml
pause
'@
Set-Content -Path (Join-Path $Target "start_agent.bat") -Value $startBat -Encoding ASCII

Write-Host "Done. Edit agent\config.windows.yaml then run start_agent.bat"

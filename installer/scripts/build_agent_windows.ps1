$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$DIST = Join-Path $ROOT "dist"
$SPECS = Join-Path $ROOT "installer\specs"
$AGENT = Join-Path $ROOT "agent"

Write-Host "=== Build Ubuntu Monitor Agent (Windows) ==="

try {
    python -c "import PyInstaller, psutil, requests, yaml" 2>$null
} catch {
    throw "Install build deps: pip install pyinstaller psutil requests pyyaml"
}

$env:PYTHONPATH = $AGENT
Push-Location $SPECS
python -m PyInstaller --noconfirm --clean agent_windows.spec
Pop-Location
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

$OUT = Join-Path $DIST "ubuntu-monitor-agent-windows"
$built = Join-Path $SPECS "dist\ubuntu-monitor-agent-windows"
if (-not (Test-Path $built)) { throw "Build failed - missing $built" }
if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
New-Item -ItemType Directory -Path $OUT -Force | Out-Null
Copy-Item -Path (Join-Path $built "*") -Destination $OUT -Recurse -Force
Copy-Item (Join-Path $ROOT "installer\templates\start_agent_windows.bat") (Join-Path $OUT "start_agent.bat") -Force

Write-Host ""
Write-Host "Built: $OUT"
Write-Host "Edit config.windows.yaml then run start_agent.bat"

$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$DIST = Join-Path $ROOT "dist"
$SPECS = Join-Path $ROOT "installer\specs"
$SERVER = Join-Path $ROOT "server"

function Get-BuildPython {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python not found"
    }
    $py = (Get-Command python).Source
    try {
        & python -c "import PyInstaller, fastapi, sqlalchemy" 2>$null
        return $py
    } catch {
        $serverVenv = Join-Path $ROOT "server\venv\Scripts\python.exe"
        if (Test-Path $serverVenv) { return $serverVenv }
        throw "Install PyInstaller and server deps on build PC: pip install pyinstaller -r server/requirements.txt"
    }
}

Write-Host "=== Build Ubuntu Monitor Server (Windows) ==="
Write-Host "Root: $ROOT"

$py = Get-BuildPython
Write-Host "Using Python: $py"

$webIndex = Join-Path $ROOT "web\dist\index.html"
if (-not (Test-Path $webIndex)) {
    Write-Host "Building web UI ..."
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm not found. Run: cd web; npm install; npm run build"
    }
    Push-Location (Join-Path $ROOT "web")
    npm run build
    Pop-Location
}

$env:PYTHONPATH = $SERVER
Push-Location $SPECS
& python -m PyInstaller --noconfirm --clean server.spec
Pop-Location
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

$OUT = Join-Path $DIST "ubuntu-monitor-server-windows"
$built = Join-Path $SPECS "dist\ubuntu-monitor-server"
if (-not (Test-Path $built)) { throw "Build failed - missing $built" }
if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
New-Item -ItemType Directory -Path $OUT -Force | Out-Null
Copy-Item -Path (Join-Path $built "*") -Destination $OUT -Recurse -Force
Copy-Item (Join-Path $ROOT "installer\templates\start_server.bat") (Join-Path $OUT "start_server.bat") -Force

Write-Host ""
Write-Host "Built: $OUT"
Write-Host "Run: $OUT\start_server.bat"

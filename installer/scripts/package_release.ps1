$ErrorActionPreference = "Stop"
Write-Host "=== Ubuntu Monitor release packages (Windows) ==="

& (Join-Path $PSScriptRoot "build_server_portable.ps1")
& (Join-Path $PSScriptRoot "build_agent_windows.ps1")

$dist = (Resolve-Path (Join-Path $PSScriptRoot "..\..\dist")).Path
$zipRoot = Join-Path $dist "releases"
New-Item -ItemType Directory -Path $zipRoot -Force | Out-Null

foreach ($name in @("ubuntu-monitor-server-portable-windows", "ubuntu-monitor-agent-windows")) {
    $folder = Join-Path $dist $name
    if (Test-Path $folder) {
        $zip = Join-Path $zipRoot "$name.zip"
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path $folder -DestinationPath $zip -Force
        Write-Host "ZIP: $zip"
    }
}

Write-Host ""
Write-Host "Release ZIPs in dist\releases\"

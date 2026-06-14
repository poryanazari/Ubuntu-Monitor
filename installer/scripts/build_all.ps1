$ErrorActionPreference = "Stop"
Write-Host "Building portable server + compiled Windows agent ..."
& (Join-Path $PSScriptRoot "build_server_portable.ps1")
& (Join-Path $PSScriptRoot "build_agent_windows.ps1")
Write-Host ""
Write-Host "Packages in dist\"

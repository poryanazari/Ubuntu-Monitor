@echo off
cd /d "%~dp0"
echo Starting Ubuntu Monitor server...
echo Dashboard: http://localhost:8000
ubuntu-monitor-server.exe
pause

@echo off
cd /d "%~dp0"
python agent_windows.py -c config.windows.yaml
pause

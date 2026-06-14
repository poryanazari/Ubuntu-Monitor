@echo off
cd /d "%~dp0"
echo Ubuntu Monitor Agent (Windows)
if not exist config.windows.yaml (
    copy config.windows.yaml.example config.windows.yaml
    echo Created config.windows.yaml — edit server_url and agent_key, then run again.
    pause
    exit /b 1
)
ubuntu-monitor-agent.exe -c config.windows.yaml

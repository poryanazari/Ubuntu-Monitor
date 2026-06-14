#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Ubuntu Monitor Agent (Linux)"
if [ ! -f config.linux.yaml ]; then
  cp config.linux.yaml.example config.linux.yaml
  echo "Created config.linux.yaml — edit server_url and agent_key, then run again."
  exit 1
fi
./ubuntu-monitor-agent -c config.linux.yaml

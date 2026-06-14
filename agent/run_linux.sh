#!/bin/bash
cd "$(dirname "$0")"
python3 agent_linux.py -c config.linux.yaml

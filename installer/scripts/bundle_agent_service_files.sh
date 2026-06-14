#!/bin/bash
# Bundle systemd install helpers into a Linux agent package directory.
set -euo pipefail
TARGET="${1:?usage: bundle_agent_service_files.sh <package_dir>}"

ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
TEMPLATES="$ROOT/installer/templates"

cp "$TEMPLATES/ubuntu-monitor-agent.service" "$TARGET/"
cp "$TEMPLATES/install_service_linux.sh" "$TARGET/install_service.sh"
cp "$TEMPLATES/uninstall_service_linux.sh" "$TARGET/uninstall_service.sh"
chmod +x "$TARGET/install_service.sh" "$TARGET/uninstall_service.sh"

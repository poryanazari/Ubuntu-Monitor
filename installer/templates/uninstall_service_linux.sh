#!/bin/bash
# Remove Ubuntu Monitor agent systemd service.
set -euo pipefail

SERVICE_NAME="ubuntu-monitor-agent"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
INSTALL_DIR="${1:-/opt/ubuntu-monitor-agent}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo $0 [install_dir]"
  exit 1
fi

if systemctl is-active --quiet "$SERVICE_NAME"; then
  systemctl stop "$SERVICE_NAME"
fi
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
  systemctl disable "$SERVICE_NAME"
fi
if [ -f "$UNIT_PATH" ]; then
  rm -f "$UNIT_PATH"
fi
systemctl daemon-reload

echo "Service $SERVICE_NAME removed."
echo "Application files in $INSTALL_DIR were not deleted."
echo "To remove them: rm -rf $INSTALL_DIR"

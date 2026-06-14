#!/bin/bash
# Install Ubuntu Monitor agent as a systemd service (Linux).
# Usage: sudo ./install_service.sh [install_dir]
set -euo pipefail

SERVICE_NAME="ubuntu-monitor-agent"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${1:-/opt/ubuntu-monitor-agent}"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo $0 [install_dir]"
  exit 1
fi

detect_layout() {
  if [ -f "$SCRIPT_DIR/ubuntu-monitor-agent" ]; then
    MODE="compiled"
    return
  fi
  if [ -d "$SCRIPT_DIR/agent" ] && [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    MODE="portable"
    return
  fi
  if [ -d "$SCRIPT_DIR/agent" ] && command -v python3 >/dev/null 2>&1; then
    MODE="python"
    return
  fi
  echo "Unknown package layout in $SCRIPT_DIR"
  exit 1
}

copy_to_install_dir() {
  if [ "$SCRIPT_DIR" = "$INSTALL_DIR" ]; then
    echo "Using install directory: $INSTALL_DIR"
    return
  fi
  echo "Copying agent to $INSTALL_DIR ..."
  mkdir -p "$INSTALL_DIR"
  if [ "$MODE" = "compiled" ]; then
    cp -a "$SCRIPT_DIR/ubuntu-monitor-agent" "$INSTALL_DIR/"
    cp -a "$SCRIPT_DIR/config.linux.yaml.example" "$INSTALL_DIR/" 2>/dev/null || true
    if [ -f "$SCRIPT_DIR/config.linux.yaml" ]; then
      cp -a "$SCRIPT_DIR/config.linux.yaml" "$INSTALL_DIR/"
    fi
  else
    cp -a "$SCRIPT_DIR/agent" "$INSTALL_DIR/"
    if [ -d "$SCRIPT_DIR/venv" ]; then
      cp -a "$SCRIPT_DIR/venv" "$INSTALL_DIR/"
    fi
  fi
  cp "$SCRIPT_DIR/install_service.sh" "$INSTALL_DIR/" 2>/dev/null || true
  cp "$SCRIPT_DIR/uninstall_service.sh" "$INSTALL_DIR/" 2>/dev/null || true
  cp "$SCRIPT_DIR/ubuntu-monitor-agent.service" "$INSTALL_DIR/" 2>/dev/null || true
}

ensure_config() {
  if [ "$MODE" = "compiled" ]; then
    CFG="$INSTALL_DIR/config.linux.yaml"
    EXAMPLE="$INSTALL_DIR/config.linux.yaml.example"
  else
    CFG="$INSTALL_DIR/agent/config.linux.yaml"
    EXAMPLE="$INSTALL_DIR/agent/config.linux.yaml.example"
  fi
  if [ ! -f "$CFG" ] && [ -f "$EXAMPLE" ]; then
    cp "$EXAMPLE" "$CFG"
    echo "Created $CFG — edit server_url and agent_key before starting."
  fi
  if [ ! -f "$CFG" ]; then
    echo "Missing config: $CFG"
    exit 1
  fi
}

build_exec_start() {
  if [ "$MODE" = "compiled" ]; then
    chmod +x "$INSTALL_DIR/ubuntu-monitor-agent"
    WORKING_DIR="$INSTALL_DIR"
    EXEC_START="$INSTALL_DIR/ubuntu-monitor-agent -c $INSTALL_DIR/config.linux.yaml"
  elif [ "$MODE" = "portable" ]; then
    WORKING_DIR="$INSTALL_DIR/agent"
    EXEC_START="$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/agent/agent_linux.py -c $INSTALL_DIR/agent/config.linux.yaml"
  else
    WORKING_DIR="$INSTALL_DIR/agent"
    EXEC_START="$(command -v python3) $INSTALL_DIR/agent/agent_linux.py -c $INSTALL_DIR/agent/config.linux.yaml"
  fi
}

write_unit() {
  TEMPLATE="$(dirname "$0")/ubuntu-monitor-agent.service"
  if [ ! -f "$TEMPLATE" ]; then
    TEMPLATE="$SCRIPT_DIR/ubuntu-monitor-agent.service"
  fi
  if [ ! -f "$TEMPLATE" ]; then
    echo "Missing ubuntu-monitor-agent.service template"
    exit 1
  fi
  sed \
    -e "s|__WORKING_DIR__|$WORKING_DIR|g" \
    -e "s|__EXEC_START__|$EXEC_START|g" \
    "$TEMPLATE" > "$UNIT_PATH"
}

install_service() {
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
  fi
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl start "$SERVICE_NAME"
}

detect_layout
copy_to_install_dir
ensure_config
build_exec_start
write_unit
install_service

echo ""
echo "Service installed: $SERVICE_NAME"
echo "Install dir: $INSTALL_DIR"
echo "Status:  systemctl status $SERVICE_NAME"
echo "Logs:    journalctl -u $SERVICE_NAME -f"

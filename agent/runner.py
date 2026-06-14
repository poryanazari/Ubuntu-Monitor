#!/usr/bin/env python3
"""Shared agent runner for Linux and Windows."""

import argparse
import signal
import sys
import time

import requests
import yaml

from collector import build_report, get_platform_name


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def send_report(server_url: str, agent_key: str, report: dict) -> bool:
    url = f"{server_url.rstrip('/')}/api/agent/report"
    try:
        resp = requests.post(
            url,
            json=report,
            headers={"X-Agent-Key": agent_key, "Content-Type": "application/json"},
            timeout=60,
        )
        return resp.status_code == 200
    except requests.RequestException as e:
        print(f"[agent] Failed to send report: {e}")
        return False


def run_agent(config_path: str, platform_label: str) -> None:
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"[agent] Config not found: {config_path}")
        sys.exit(1)

    server_url = config.get("server_url", "http://localhost:8000")
    agent_key = config.get("agent_key", "")
    interval = int(config.get("interval_seconds", 30))

    if not agent_key or agent_key == "YOUR_AGENT_KEY_HERE":
        print("[agent] Set agent_key in config.yaml (copy from dashboard)")
        sys.exit(1)

    detected = get_platform_name()
    print(f"[agent] {platform_label} — platform={detected}, server={server_url}, interval={interval}s")

    running = True

    def stop(_sig, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    while running:
        report = build_report()
        ok = send_report(server_url, agent_key, report)
        status = "OK" if ok else "FAILED"
        m = report["metrics"]
        print(
            f"[agent] Report {status} — CPU {m['cpu_percent']}% "
            f"RAM {m['memory_percent']}% Connections {m['connection_count']}"
        )
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    print("[agent] Stopped")


def main():
    parser = argparse.ArgumentParser(description="Ubuntu Monitor Agent")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--platform", default="auto", choices=["auto", "linux", "windows"])
    args = parser.parse_args()

    import platform as plat
    if args.platform == "linux" and plat.system() != "Linux":
        print("[agent] Warning: running Linux agent on non-Linux OS")
    if args.platform == "windows" and plat.system() != "Windows":
        print("[agent] Warning: running Windows agent on non-Windows OS")

    label = args.platform if args.platform != "auto" else plat.system()
    run_agent(args.config, label)

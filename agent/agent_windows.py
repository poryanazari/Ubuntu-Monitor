#!/usr/bin/env python3
"""Ubuntu Monitor Agent for Windows servers."""

import platform
import sys

from runner import run_agent

if __name__ == "__main__":
    import argparse

    if platform.system() != "Windows":
        print(f"[agent-windows] Warning: expected Windows, got {platform.system()}")

    parser = argparse.ArgumentParser(description="Ubuntu Monitor Agent (Windows)")
    parser.add_argument("-c", "--config", default="config.windows.yaml")
    args = parser.parse_args()
    run_agent(args.config, "Windows")

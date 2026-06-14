#!/usr/bin/env python3
"""Ubuntu Monitor Agent for Linux servers."""

import platform
import sys

from runner import run_agent

if __name__ == "__main__":
    import argparse

    if platform.system() != "Linux":
        print(f"[agent-linux] Warning: expected Linux, got {platform.system()}")

    parser = argparse.ArgumentParser(description="Ubuntu Monitor Agent (Linux)")
    parser.add_argument("-c", "--config", default="config.linux.yaml")
    args = parser.parse_args()
    run_agent(args.config, "Linux")

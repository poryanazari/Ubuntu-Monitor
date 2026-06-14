#!/usr/bin/env python3
"""Ubuntu Monitor Agent — auto-detects Linux or Windows."""

from runner import run_agent

if __name__ == "__main__":
    import argparse
    import platform

    parser = argparse.ArgumentParser(description="Ubuntu Monitor Agent (auto)")
    parser.add_argument("-c", "--config", default="config.yaml")
    args = parser.parse_args()
    run_agent(args.config, platform.system())

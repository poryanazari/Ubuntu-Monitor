"""PyInstaller entry point for Ubuntu Monitor agent (Windows)."""

import os
import sys
from pathlib import Path

INSTALLER_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = INSTALLER_DIR.parent / "agent"

if getattr(sys, "frozen", False):
    AGENT_ROOT = Path(sys.executable).parent
else:
    AGENT_ROOT = AGENT_DIR

os.chdir(AGENT_ROOT)
if not getattr(sys, "frozen", False) and str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from runner import run_agent

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ubuntu Monitor Agent (Windows)")
    parser.add_argument("-c", "--config", default="config.windows.yaml")
    args = parser.parse_args()
    run_agent(args.config, "Windows")

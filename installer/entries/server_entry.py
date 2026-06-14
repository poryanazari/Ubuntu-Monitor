"""PyInstaller entry point for Ubuntu Monitor server."""

import os
import sys
from pathlib import Path

INSTALLER_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = INSTALLER_DIR.parent
SERVER_DIR = PROJECT_ROOT / "server"

if getattr(sys, "frozen", False):
    DATA_DIR = Path(sys.executable).parent
    STATIC_DIR = DATA_DIR / "web" / "dist"
else:
    DATA_DIR = SERVER_DIR
    STATIC_DIR = PROJECT_ROOT / "web" / "dist"

os.environ.setdefault("UBUNTU_MONITOR_DATA_DIR", str(DATA_DIR))
if STATIC_DIR.is_dir():
    os.environ.setdefault("UBUNTU_MONITOR_STATIC_DIR", str(STATIC_DIR))

os.chdir(DATA_DIR)
if not getattr(sys, "frozen", False) and str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("UBUNTU_MONITOR_PORT", "8000"))
    host = os.environ.get("UBUNTU_MONITOR_HOST", "0.0.0.0")
    print(f"Ubuntu Monitor server - http://localhost:{port}")
    print(f"Data directory: {DATA_DIR}")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")

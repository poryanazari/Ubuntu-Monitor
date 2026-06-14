"""Shared helpers for collectors."""

import subprocess
from typing import Any


def run_cmd(cmd: list[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return ""


def read_file(path: str, max_bytes: int = 65536) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except OSError:
        return ""


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

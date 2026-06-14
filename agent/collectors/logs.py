"""Collect system logs for persistent storage."""

import hashlib
import re
from datetime import datetime
from typing import Any

from collectors.common import read_file, run_cmd

ERROR_PATTERN = re.compile(r"error|fail|critical|panic|warning|warn", re.I)


def _level_from_line(line: str) -> str:
    lower = line.lower()
    if re.search(r"critical|panic|emerg", lower):
        return "critical"
    if re.search(r"error|fail", lower):
        return "error"
    if re.search(r"warn", lower):
        return "warning"
    return "info"


def _make_entry(source: str, line: str, ts: str | None = None) -> dict[str, str]:
    return {
        "source": source,
        "level": _level_from_line(line),
        "message": line.strip()[-2000:],
        "timestamp": ts or datetime.utcnow().isoformat(),
    }


def collect_logs_linux() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    sources = [
        ("/var/log/syslog", "syslog"),
        ("/var/log/auth.log", "auth"),
        ("/var/log/kern.log", "kernel"),
        ("/var/log/nginx/error.log", "nginx"),
        ("/var/log/apache2/error.log", "apache"),
    ]
    for path, source in sources:
        content = read_file(path, max_bytes=65536)
        if not content:
            continue
        lines = content.strip().split("\n")[-80:]
        for line in lines:
            if line.strip():
                entries.append(_make_entry(source, line))

    journal = run_cmd(["journalctl", "-n", "50", "--no-pager", "-o", "short-iso"], timeout=15)
    if journal:
        for line in journal.strip().split("\n"):
            if line.strip():
                entries.append(_make_entry("journal", line))
    return entries[:400]


def collect_logs_windows() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for log_name in ("System", "Application", "Security"):
        out = run_cmd(
            ["wevtutil", "qe", log_name, "/c:40", "/rd:true", "/f:text"],
            timeout=20,
        )
        if out:
            for line in out.strip().split("\n"):
                if line.strip() and not line.startswith("Event["):
                    entries.append(_make_entry(log_name, line))
    return entries[:400]


def collect_logs() -> list[dict[str, str]]:
    import platform
    if platform.system() == "Windows":
        return collect_logs_windows()
    return collect_logs_linux()


def log_hash(entry: dict[str, str]) -> str:
    raw = f"{entry.get('source')}:{entry.get('message')}"
    return hashlib.md5(raw.encode("utf-8", errors="replace")).hexdigest()

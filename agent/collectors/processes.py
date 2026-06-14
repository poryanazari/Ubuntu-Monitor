"""Shared process metrics (all platforms)."""

from typing import Any

import psutil


def collect_processes() -> dict[str, Any]:
    total = 0
    zombies = 0
    procs: list[dict[str, Any]] = []

    for proc in psutil.process_iter(["pid", "name", "status", "cpu_percent", "memory_percent", "username"]):
        try:
            pinfo = proc.info
            total += 1
            if pinfo["status"] == psutil.STATUS_ZOMBIE:
                zombies += 1
            procs.append({
                "pid": pinfo["pid"],
                "name": pinfo["name"] or "",
                "cpu_percent": round(pinfo.get("cpu_percent") or 0, 2),
                "memory_percent": round(pinfo.get("memory_percent") or 0, 2),
                "username": pinfo.get("username") or "",
                "status": pinfo["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "total": total,
        "zombie_count": zombies,
        "top_cpu": sorted(procs, key=lambda p: p["cpu_percent"], reverse=True)[:10],
        "top_memory": sorted(procs, key=lambda p: p["memory_percent"], reverse=True)[:10],
    }

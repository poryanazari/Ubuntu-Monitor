"""External connectivity: latency, DNS, port checks."""

import socket
import subprocess
import time
from typing import Any

from collectors.common import run_cmd


def ping_target(host: str) -> dict[str, Any]:
    latency_ms = None
    packet_loss = 100.0

    import platform as plat
    if plat.system() == "Windows":
        out = run_cmd(["ping", "-n", "2", "-w", "1000", host], timeout=8)
    else:
        out = run_cmd(["ping", "-c", "2", "-W", "2", host], timeout=8)

    if out:
        import re
        m = re.search(r"(\d+)% packet loss", out)
        if m:
            packet_loss = float(m.group(1))
        m = re.search(r"min/avg/max[^=]*=\s*[\d.]+/([\d.]+)/", out)
        if m:
            latency_ms = round(float(m.group(1)), 2)
        else:
            m = re.search(r"Average\s*=\s*([\d.]+)ms", out, re.I)
            if m:
                latency_ms = round(float(m.group(1)), 2)

    return {"target": host, "latency_ms": latency_ms, "packet_loss_percent": packet_loss}


def check_dns() -> dict[str, Any]:
    ok = False
    resolved = ""
    out = run_cmd(["host", "google.com"])
    if out and "has address" in out:
        ok = True
        resolved = out.split("has address")[1].strip().split()[0]
    else:
        try:
            resolved = socket.gethostbyname("google.com")
            ok = True
        except OSError:
            pass
    return {"ok": ok, "resolved": resolved, "query": "google.com"}


def check_port(host: str, port: int, timeout: float = 0.5) -> dict[str, Any]:
    open_ = False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            open_ = True
    except OSError:
        pass
    return {"host": host, "port": port, "open": open_}


def collect_connectivity() -> dict[str, Any]:
    targets = ["8.8.8.8", "1.1.1.1"]
    latency_checks = [ping_target(t) for t in targets]
    dns = check_dns()
    ports = [check_port("127.0.0.1", p) for p in (22, 80, 443, 3306, 5432, 6379)]

    return {
        "latency": latency_checks,
        "dns": dns,
        "ports": ports,
    }

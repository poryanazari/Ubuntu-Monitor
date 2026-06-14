"""Shared HTTP/SSL checks (all platforms)."""

import socket
import ssl
import time
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen

import psutil


def http_check(url: str, timeout: float = 5.0) -> dict[str, Any]:
    start = time.time()
    status_code = 0
    error = ""
    try:
        req = Request(url, headers={"User-Agent": "Ubuntu-Monitor-Agent/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
    except Exception as e:
        error = str(e)[:200]
        if hasattr(e, "code"):
            status_code = e.code
    elapsed_ms = round((time.time() - start) * 1000, 2)
    return {
        "url": url,
        "status_code": status_code,
        "response_ms": elapsed_ms,
        "ok": status_code in (200, 201, 204, 301, 302),
        "error": error,
    }


def ssl_expiry(hostname: str, port: int = 443) -> dict[str, Any]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return {"hostname": hostname, "valid": False, "days_until_expiry": None}
                expiry = cert.get("notAfter")
                if expiry:
                    exp_date = datetime.strptime(expiry, "%b %d %H:%M:%S %Y %Z")
                    days = (exp_date - datetime.utcnow()).days
                    return {
                        "hostname": hostname,
                        "valid": days > 0,
                        "days_until_expiry": days,
                        "expires": expiry,
                    }
    except Exception as e:
        return {"hostname": hostname, "valid": False, "error": str(e)[:100]}
    return {"hostname": hostname, "valid": False}


def collect_http_checks() -> list[dict[str, Any]]:
    urls = ["http://127.0.0.1/", "http://localhost/"]
    for port, scheme in [(80, "http"), (443, "https"), (8080, "http")]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                url = f"{scheme}://127.0.0.1:{port}/"
                if url not in urls:
                    urls.append(url)
        except OSError:
            pass
    return [http_check(url) for url in urls[:5]]


def collect_app_memory() -> list[dict[str, Any]]:
    app_memory: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["name", "pid", "memory_info"]):
        try:
            name = (proc.info["name"] or "").lower()
            if any(k in name for k in ("python", "node", "java", "php", "gunicorn", "uwsgi", "w3wp")):
                mem = proc.info["memory_info"]
                if mem:
                    app_memory.append({
                        "name": proc.info["name"],
                        "pid": proc.info["pid"],
                        "memory_mb": round(mem.rss / (1024 ** 2), 2),
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(app_memory, key=lambda x: x["memory_mb"], reverse=True)[:15]

"""Windows-specific monitoring: services, registry, event log."""

import os
import platform
import re
from typing import Any

import psutil

from collectors.common import run_cmd
from collectors.processes import collect_processes
from collectors.web_common import collect_app_memory, collect_http_checks, ssl_expiry

MONITORED_SERVICES = [
    "sshd", "OpenSSH", "W3SVC", "nginx", "Apache2.4", "MySQL", "MSSQLSERVER",
    "postgresql", "Redis", "docker", "Dnscache", "EventLog", "WinRM",
]

PLATFORM = "windows"
PRIMARY_DISK_MOUNT = "C:\\"


def _powershell(script: str, timeout: int = 30) -> str:
    return run_cmd(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=timeout,
    )


def collect_log_errors() -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    out = run_cmd(
        ["wevtutil", "qe", "System", "/q:*[System[(Level=2 or Level=3)]]", "/c:15", "/rd:true", "/f:text"],
        timeout=20,
    )
    if out:
        for line in out.strip().split("\n"):
            if line.strip():
                errors.append({"source": "System", "message": line[-300:]})
    return errors[:30]


def collect_ntp() -> dict[str, Any]:
    synced = False
    offset_ms = None
    out = run_cmd(["w32tm", "/query", "/status"])
    if out:
        synced = "Leap Indicator: 0" in out or "Source:" in out
        m = re.search(r"Phase Offset:\s*([-\d.]+)s", out)
        if m:
            offset_ms = round(float(m.group(1)) * 1000, 2)
    return {
        "synced": synced,
        "service": "w32time",
        "offset_ms": offset_ms,
        "kernel_version": platform.version(),
        "platform": platform.platform(),
    }


def collect_logins() -> dict[str, Any]:
    users_out = run_cmd(["query", "user"])
    logged_in = 0
    user_list: list[str] = []
    if users_out:
        lines = [l for l in users_out.strip().split("\n") if l.strip() and "USERNAME" not in l.upper()]
        logged_in = len(lines)
        user_list = lines[:20]

    failed = 0
    evt = _powershell(
        "(Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 20 "
        "-ErrorAction SilentlyContinue | Measure-Object).Count",
        timeout=15,
    )
    if evt.strip().isdigit():
        failed = int(evt.strip())

    return {
        "logged_in_users": logged_in,
        "failed_ssh_attempts": failed,
        "failed_login_attempts": failed,
        "user_list": user_list,
    }


def collect_services() -> list[dict[str, str]]:
    items = []
    out = _powershell(
        "Get-Service | Where-Object { $_.Name -match 'ssh|nginx|apache|mysql|postgres|redis|docker|W3SVC|MSSQL' } "
        "| Select-Object Name, Status | ConvertTo-Json -Compress"
    )
    if not out.strip():
        return items

    import json
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        for svc in data:
            status = str(svc.get("Status", ""))
            items.append({
                "name": svc.get("Name", ""),
                "active": status,
                "sub_state": status,
                "status": "up" if status.lower() == "running" else status.lower(),
            })
    except json.JSONDecodeError:
        pass
    return items


def collect_os() -> dict[str, Any]:
    return {
        "platform": PLATFORM,
        "processes": collect_processes(),
        "log_errors": collect_log_errors(),
        "system": collect_ntp(),
        "logins": collect_logins(),
        "services": collect_services(),
    }


def collect_security() -> dict[str, Any]:
    expected_ports = {22, 80, 443, 3306, 5432, 6379, 8080, 3389, 5985, 5986}
    open_ports: list[dict[str, Any]] = []
    unexpected_ports: list[int] = []

    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr:
                port = conn.laddr.port
                if port not in [p["port"] for p in open_ports]:
                    open_ports.append({"port": port, "addr": f"{conn.laddr.ip}:{port}"})
                    if port not in expected_ports and port > 1024:
                        unexpected_ports.append(port)
    except (psutil.AccessDenied, PermissionError):
        pass

    privileged = []
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            user = (proc.info.get("username") or "").upper()
            if user.endswith("SYSTEM") or "ADMIN" in user:
                privileged.append({"pid": proc.info["pid"], "name": proc.info["name"] or ""})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    failed = collect_logins().get("failed_login_attempts", 0)

    large_logs = []
    log_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Logs")
    if os.path.isdir(log_dir):
        try:
            for entry in os.scandir(log_dir):
                if entry.is_file() and entry.stat().st_size > 50 * 1024 * 1024:
                    large_logs.append({
                        "path": entry.path,
                        "size_mb": round(entry.stat().st_size / (1024 ** 2), 2),
                    })
        except OSError:
            pass

    updates = 0
    # Skip slow Windows Update COM scan during regular agent cycles

    return {
        "platform": PLATFORM,
        "failed_ssh_attempts": failed,
        "failed_login_attempts": failed,
        "open_ports": sorted(open_ports, key=lambda x: x["port"]),
        "unexpected_ports": sorted(set(unexpected_ports))[:20],
        "privileged_process_count": len(privileged),
        "privileged_processes_sample": privileged[:15],
        "root_process_count": len(privileged),
        "root_processes_sample": privileged[:15],
        "large_logs": large_logs[:10],
        "os_version": platform.version(),
        "security_updates_available": updates,
    }


def detect_packages() -> list[dict[str, str]]:
    """Only notable installed software — avoids slow full registry scan."""
    items = []
    filter_names = "nginx|apache|mysql|postgres|redis|docker|python|node|java|openssh|iis|sql|mongodb|nginx"
    out = _powershell(
        f"Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
        f"HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        f"| Where-Object {{ $_.DisplayName -match '{filter_names}' }} "
        f"| Select-Object DisplayName, DisplayVersion "
        f"| ConvertTo-Json -Compress",
        timeout=20,
    )
    if not out.strip():
        return items

    import json
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        for pkg in data[:300]:
            items.append({
                "name": pkg.get("DisplayName", ""),
                "version": pkg.get("DisplayVersion", "") or "",
                "category": "package",
                "status": "installed",
                "details": "registry",
            })
    except json.JSONDecodeError:
        pass
    return items


def detect_services_software() -> list[dict[str, str]]:
    items = []
    names = "ssh*,nginx*,apache*,mysql*,postgres*,redis*,docker*,W3SVC,MSSQL*"
    out = _powershell(
        f"Get-Service -Name {names} -ErrorAction SilentlyContinue "
        f"| Select-Object Name, Status | ConvertTo-Json -Compress",
        timeout=15,
    )
    if not out.strip():
        return items

    import json
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        for svc in data:
            name = svc.get("Name", "")
            status = str(svc.get("Status", ""))
            if any(s.lower() in name.lower() for s in MONITORED_SERVICES) or status.lower() in ("running", "stopped"):
                if any(k in name.lower() for k in ("ssh", "nginx", "apache", "mysql", "postgres", "redis", "docker", "w3svc", "mssql")):
                    items.append({
                        "name": name,
                        "version": "",
                        "category": "service",
                        "status": status.lower(),
                        "details": "windows-service",
                    })
    except json.JSONDecodeError:
        pass
    return items[:100]


def detect_running_processes() -> list[dict[str, str]]:
    keywords = {"nginx", "httpd", "mysqld", "postgres", "redis", "docker", "node", "python", "java", "w3wp"}
    seen, items = set(), []
    for proc in psutil.process_iter(["name", "pid", "status"]):
        try:
            name = proc.info["name"] or ""
            key = name.lower().replace(".exe", "")
            if key in keywords and key not in seen:
                seen.add(key)
                items.append({
                    "name": name, "version": "", "category": "process",
                    "status": proc.info["status"] or "running",
                    "details": f"pid={proc.info['pid']}",
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return items


def detect_software() -> list[dict[str, str]]:
    services = detect_services_software()
    processes = detect_running_processes()
    packages = detect_packages()
    combined = services + processes + packages
    return combined[:600]


def collect_web() -> dict[str, Any]:
    checks = collect_http_checks()
    iis = run_cmd(["sc", "query", "W3SVC"])
    iis_status = "running" if "RUNNING" in iis.upper() else ("not_installed" if "1060" in iis else "stopped")
    return {
        "platform": PLATFORM,
        "http_checks": checks,
        "ssl_checks": [ssl_expiry("127.0.0.1")],
        "app_memory": collect_app_memory(),
        "nginx_status": "not_installed",
        "apache_status": "not_installed",
        "iis_status": iis_status,
        "error_rate_percent": round(sum(1 for c in checks if not c["ok"]) / max(len(checks), 1) * 100, 2),
        "requests_per_sec": None,
        "queue_length": None,
    }

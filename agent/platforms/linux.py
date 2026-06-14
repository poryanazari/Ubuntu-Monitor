"""Linux-specific monitoring: systemd, dpkg, syslog, apt."""

import platform
import re
from typing import Any

from collectors.common import read_file, run_cmd
from collectors.processes import collect_processes
from collectors.web_common import collect_app_memory, collect_http_checks, ssl_expiry

MONITORED_SERVICES = [
    "sshd", "ssh", "cron", "crond", "nginx", "apache2", "httpd",
    "mysql", "mariadb", "postgresql", "redis", "docker", "fail2ban",
]

PLATFORM = "linux"
PRIMARY_DISK_MOUNT = "/"


def collect_log_errors() -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    sources = [
        ("/var/log/syslog", "syslog"),
        ("/var/log/kern.log", "kernel"),
        ("/var/log/auth.log", "auth"),
    ]
    error_pattern = re.compile(r"error|fail|critical|panic|oom|segfault", re.I)

    for path, source in sources:
        content = read_file(path, max_bytes=32768)
        if not content:
            continue
        for line in content.strip().split("\n")[-50:]:
            if error_pattern.search(line):
                errors.append({"source": source, "message": line[-300:]})
        if len(errors) >= 20:
            break

    dmesg = run_cmd(["dmesg", "--level=err,warn", "-T"], timeout=10)
    if dmesg:
        for line in dmesg.strip().split("\n")[-10:]:
            errors.append({"source": "dmesg", "message": line[-300:]})
    return errors[:30]


def collect_ntp() -> dict[str, Any]:
    offset_ms = None
    synced = False
    service = "unknown"

    timedate = run_cmd(["timedatectl", "status"])
    if timedate:
        synced = "System clock synchronized: yes" in timedate
        m = re.search(r"NTP service:\s*(\w+)", timedate)
        service = m.group(1) if m else service

    chrony = run_cmd(["chronyc", "tracking"])
    if chrony:
        m = re.search(r"System time\s*:\s*([\d.+-]+)\s*seconds", chrony)
        if m:
            offset_ms = round(float(m.group(1)) * 1000, 2)

    if offset_ms is None:
        ntpq = run_cmd(["ntpq", "-c", "rv 0 offset"])
        if ntpq:
            m = re.search(r"offset=([\d.+-]+)", ntpq)
            if m:
                offset_ms = round(float(m.group(1)), 2)

    return {
        "synced": synced,
        "service": service,
        "offset_ms": offset_ms,
        "kernel_version": platform.release(),
        "platform": platform.platform(),
    }


def collect_logins() -> dict[str, Any]:
    users_out = run_cmd(["who"])
    logged_in = len(users_out.strip().split("\n")) if users_out.strip() else 0
    failed_ssh = 0
    auth_log = read_file("/var/log/auth.log", max_bytes=65536)
    if auth_log:
        failed_ssh = len(re.findall(r"Failed password|authentication failure", auth_log, re.I))
    return {
        "logged_in_users": logged_in,
        "failed_ssh_attempts": failed_ssh,
        "user_list": users_out.strip().split("\n")[:20] if users_out else [],
    }


def collect_services() -> list[dict[str, str]]:
    items = []
    out = run_cmd(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"])
    if not out:
        return items
    for line in out.strip().split("\n"):
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[0].replace(".service", "")
        sub = parts[3] if len(parts) > 3 else ""
        if name in MONITORED_SERVICES or any(s in name for s in MONITORED_SERVICES):
            items.append({
                "name": name,
                "active": parts[2] if len(parts) > 2 else "",
                "sub_state": sub,
                "status": "up" if sub == "running" else sub,
            })
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
    import os
    import psutil

    failed_ssh = 0
    auth_log = read_file("/var/log/auth.log", max_bytes=131072)
    if auth_log:
        failed_ssh = len(re.findall(r"Failed password|authentication failure", auth_log, re.I))

    expected_ports = {22, 80, 443, 3306, 5432, 6379, 8080}
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

    root_processes = []
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            if proc.info.get("username") == "root":
                root_processes.append({"pid": proc.info["pid"], "name": proc.info["name"] or ""})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    large_logs = []
    if os.path.isdir("/var/log"):
        try:
            for entry in os.scandir("/var/log"):
                if entry.is_file() and entry.name.endswith(".log"):
                    size_mb = entry.stat().st_size / (1024 ** 2)
                    if size_mb > 50:
                        large_logs.append({"path": entry.path, "size_mb": round(size_mb, 2)})
        except OSError:
            pass

    apt = run_cmd(["apt", "list", "--upgradable"])
    updates = len([l for l in apt.split("\n") if "/" in l and "Listing" not in l]) if apt else 0

    return {
        "platform": PLATFORM,
        "failed_ssh_attempts": failed_ssh,
        "failed_login_attempts": failed_ssh,
        "open_ports": sorted(open_ports, key=lambda x: x["port"]),
        "unexpected_ports": sorted(set(unexpected_ports))[:20],
        "privileged_process_count": len(root_processes),
        "privileged_processes_sample": root_processes[:15],
        "root_process_count": len(root_processes),
        "root_processes_sample": root_processes[:15],
        "large_logs": large_logs[:10],
        "os_version": run_cmd(["uname", "-r"]).strip(),
        "security_updates_available": updates,
    }


def detect_packages() -> list[dict[str, str]]:
    items = []
    dpkg_out = run_cmd(["dpkg-query", "-W", "-f=${Package}|${Version}\n"])
    if dpkg_out:
        for line in dpkg_out.strip().split("\n"):
            if "|" in line:
                name, version = line.split("|", 1)
                items.append({
                    "name": name, "version": version,
                    "category": "package", "status": "installed", "details": "dpkg",
                })
        return items[:500]

    rpm_out = run_cmd(["rpm", "-qa", "--queryformat", "%{NAME}|%{VERSION}\n"])
    if rpm_out:
        for line in rpm_out.strip().split("\n"):
            if "|" in line:
                name, version = line.split("|", 1)
                items.append({
                    "name": name, "version": version,
                    "category": "package", "status": "installed", "details": "rpm",
                })
    return items[:500]


def detect_services_software() -> list[dict[str, str]]:
    items = []
    out = run_cmd(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"])
    if not out:
        return items
    for line in out.strip().split("\n"):
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[0].replace(".service", "")
        status = parts[3] if len(parts) > 3 else "unknown"
        if any(s in name for s in MONITORED_SERVICES) or status in ("active", "running", "failed"):
            items.append({
                "name": name, "version": "", "category": "service",
                "status": status, "details": "systemd",
            })
    return items[:100]


def detect_running_processes() -> list[dict[str, str]]:
    import psutil
    keywords = {"nginx", "apache", "httpd", "mysql", "mariadb", "postgres", "redis", "docker", "node", "python", "java", "mongodb"}
    seen, items = set(), []
    for proc in psutil.process_iter(["name", "pid", "status"]):
        try:
            name = proc.info["name"] or ""
            key = name.lower()
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
    packages = detect_packages()
    services = detect_services_software()
    processes = detect_running_processes()
    combined = services + processes
    if len(packages) < 200:
        combined.extend(packages)
    else:
        notable = re.compile(r"nginx|apache|mysql|mariadb|postgres|redis|docker|python|node|java|php|openssh|zabbix", re.I)
        combined.extend([p for p in packages if notable.search(p["name"])][:100])
    return combined[:600]


def collect_web() -> dict[str, Any]:
    checks = collect_http_checks()
    nginx = run_cmd(["systemctl", "is-active", "nginx"]).strip()
    apache = run_cmd(["systemctl", "is-active", "apache2"]).strip()
    return {
        "platform": PLATFORM,
        "http_checks": checks,
        "ssl_checks": [ssl_expiry("127.0.0.1")],
        "app_memory": collect_app_memory(),
        "nginx_status": nginx or "not_installed",
        "apache_status": apache or "not_installed",
        "iis_status": "not_installed",
        "error_rate_percent": round(sum(1 for c in checks if not c["ok"]) / max(len(checks), 1) * 100, 2),
        "requests_per_sec": None,
        "queue_length": None,
    }

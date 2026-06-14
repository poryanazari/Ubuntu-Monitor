"""Platform router — selects Linux or Windows collector."""

import platform
import socket
from typing import Any

import psutil

from collectors.connectivity import collect_connectivity
from collectors.containers import collect_containers
from collectors.database import collect_databases
from collectors.host import collect_host
from collectors.logs import collect_logs

if platform.system() == "Windows":
    from platforms import windows as _platform
else:
    from platforms import linux as _platform


def get_platform_name() -> str:
    return _platform.PLATFORM


def get_hostname() -> str:
    return socket.gethostname()


def get_ip_address() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def get_os_info() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def collect_metrics_from_host(host: dict[str, Any]) -> dict[str, Any]:
    cpu = host["cpu"]
    mem = host["memory"]
    net = host["network"]
    disks = host["disks"]
    primary = _platform.PRIMARY_DISK_MOUNT
    root_disk = next(
        (d for d in disks if d["mountpoint"] == primary or d["mountpoint"].startswith(primary)),
        disks[0] if disks else None,
    )

    return {
        "cpu_percent": cpu["percent"],
        "cpu_count": cpu["count"],
        "memory_total_mb": mem["total_mb"],
        "memory_used_mb": mem["used_mb"],
        "memory_percent": mem["percent"],
        "disk_total_gb": root_disk["total_gb"] if root_disk else 0,
        "disk_used_gb": root_disk["used_gb"] if root_disk else 0,
        "disk_percent": root_disk["percent"] if root_disk else 0,
        "network_bytes_sent": net["bytes_sent"],
        "network_bytes_recv": net["bytes_recv"],
        "network_sent_rate": net["sent_rate_bps"],
        "network_recv_rate": net["recv_rate_bps"],
        "connection_count": net["connection_count"],
        "load_average": cpu["load_1"],
        "uptime_seconds": host["uptime_seconds"],
    }


def collect_connections(limit: int = 200) -> list[dict[str, Any]]:
    results = []
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return results

    for conn in connections[:limit]:
        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
        pname = ""
        if conn.pid:
            try:
                pname = psutil.Process(conn.pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pname = ""
        results.append({
            "local_addr": laddr,
            "remote_addr": raddr,
            "status": conn.status,
            "pid": conn.pid or 0,
            "process_name": pname,
        })
    return results


def collect_extended(host: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "host": host or collect_host(),
        "os": _platform.collect_os(),
        "databases": collect_databases(),
        "web": _platform.collect_web(),
        "connectivity": collect_connectivity(),
        "security": _platform.collect_security(),
        "containers": collect_containers(),
    }


def build_report() -> dict[str, Any]:
    host = collect_host()
    return {
        "hostname": get_hostname(),
        "ip_address": get_ip_address(),
        "os_info": get_os_info(),
        "platform": get_platform_name(),
        "metrics": collect_metrics_from_host(host),
        "extended": collect_extended(host),
        "connections": collect_connections(),
        "software": _platform.detect_software(),
        "logs": collect_logs(),
    }

"""Host resources: CPU, memory, disk, network."""

import os
import time
from typing import Any

import psutil

_last_net: dict[str, float] = {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0, "time": time.time()}
_last_disk: dict[str, float] = {"read_bytes": 0, "write_bytes": 0, "time": time.time()}


def collect_cpu() -> dict[str, Any]:
    per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    load_1, load_5, load_15 = (0.0, 0.0, 0.0)
    if hasattr(os, "getloadavg"):
        load_1, load_5, load_15 = os.getloadavg()

    running = waiting = 0
    for proc in psutil.process_iter(["status"]):
        try:
            st = proc.info["status"]
            if st == psutil.STATUS_RUNNING:
                running += 1
            elif st in (psutil.STATUS_DISK_SLEEP, psutil.STATUS_PARKED):
                waiting += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "percent": round(psutil.cpu_percent(interval=0), 2),
        "per_core": [round(c, 2) for c in per_core],
        "count": psutil.cpu_count() or 1,
        "load_1": round(load_1, 2),
        "load_5": round(load_5, 2),
        "load_15": round(load_15, 2),
        "processes_running": running,
        "processes_waiting": waiting,
    }


def collect_memory() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total_mb": round(mem.total / (1024 ** 2), 2),
        "used_mb": round(mem.used / (1024 ** 2), 2),
        "free_mb": round(mem.free / (1024 ** 2), 2),
        "available_mb": round(mem.available / (1024 ** 2), 2),
        "cached_mb": round(getattr(mem, "cached", 0) / (1024 ** 2), 2),
        "buffers_mb": round(getattr(mem, "buffers", 0) / (1024 ** 2), 2),
        "percent": round(mem.percent, 2),
        "swap_total_mb": round(swap.total / (1024 ** 2), 2),
        "swap_used_mb": round(swap.used / (1024 ** 2), 2),
        "swap_percent": round(swap.percent, 2),
    }


def collect_disks() -> list[dict[str, Any]]:
    disks = []
    for part in psutil.disk_partitions(all=False):
        if part.fstype in ("", "squashfs"):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            inode_percent = 0.0
            if hasattr(os, "statvfs"):
                try:
                    stat = os.statvfs(part.mountpoint)
                    if stat.f_files > 0:
                        inode_percent = round((stat.f_files - stat.f_ffree) / stat.f_files * 100, 2)
                except OSError:
                    pass
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent": round(usage.percent, 2),
                "inode_percent": inode_percent,
            })
        except (PermissionError, OSError):
            continue
    return disks


def collect_disk_io() -> dict[str, Any]:
    global _last_disk
    io = psutil.disk_io_counters()
    if not io:
        return {"read_bytes_sec": 0, "write_bytes_sec": 0, "io_wait_percent": 0}

    now = time.time()
    elapsed = max(now - _last_disk["time"], 0.001)
    read_rate = (io.read_bytes - _last_disk["read_bytes"]) / elapsed
    write_rate = (io.write_bytes - _last_disk["write_bytes"]) / elapsed
    _last_disk = {"read_bytes": io.read_bytes, "write_bytes": io.write_bytes, "time": now}

    io_wait = 0.0
    for proc in psutil.process_iter(["cpu_percent"]):
        try:
            if proc.info.get("cpu_percent", 0) > 0:
                pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Approximate I/O wait from CPU times if available
    try:
        times = psutil.cpu_times_percent(interval=0)
        io_wait = round(getattr(times, "iowait", 0) or 0, 2)
    except Exception:
        pass

    return {
        "read_bytes_sec": round(read_rate, 2),
        "write_bytes_sec": round(write_rate, 2),
        "read_mb_sec": round(read_rate / (1024 ** 2), 3),
        "write_mb_sec": round(write_rate / (1024 ** 2), 3),
        "io_wait_percent": io_wait,
    }


def collect_network() -> dict[str, Any]:
    global _last_net
    net = psutil.net_io_counters()
    now = time.time()
    elapsed = max(now - _last_net["time"], 0.001)

    sent_rate = (net.bytes_sent - _last_net["bytes_sent"]) / elapsed
    recv_rate = (net.bytes_recv - _last_net["bytes_recv"]) / elapsed
    pkt_sent_rate = (net.packets_sent - _last_net["packets_sent"]) / elapsed
    pkt_recv_rate = (net.packets_recv - _last_net["packets_recv"]) / elapsed

    _last_net = {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "time": now,
    }

    tcp_states: dict[str, int] = {}
    try:
        for conn in psutil.net_connections(kind="inet"):
            st = conn.status if conn.status else "NONE"
            tcp_states[st] = tcp_states.get(st, 0) + 1
    except (psutil.AccessDenied, PermissionError):
        pass

    return {
        "bytes_sent": float(net.bytes_sent),
        "bytes_recv": float(net.bytes_recv),
        "sent_rate_bps": round(sent_rate, 2),
        "recv_rate_bps": round(recv_rate, 2),
        "sent_rate_mbps": round(sent_rate * 8 / (1024 ** 2), 3),
        "recv_rate_mbps": round(recv_rate * 8 / (1024 ** 2), 3),
        "packets_sent_rate": round(pkt_sent_rate, 2),
        "packets_recv_rate": round(pkt_recv_rate, 2),
        "errors_in": net.errin,
        "errors_out": net.errout,
        "drops_in": net.dropin,
        "drops_out": net.dropout,
        "tcp_states": tcp_states,
        "connection_count": sum(tcp_states.values()),
    }


def collect_host() -> dict[str, Any]:
    return {
        "cpu": collect_cpu(),
        "memory": collect_memory(),
        "disks": collect_disks(),
        "disk_io": collect_disk_io(),
        "network": collect_network(),
        "uptime_seconds": round(time.time() - psutil.boot_time(), 2),
    }

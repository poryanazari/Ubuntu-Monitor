"""Database monitoring: PostgreSQL, MySQL, Redis."""

import socket
from typing import Any

from collectors.common import run_cmd, safe_float


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_postgresql() -> dict[str, Any] | None:
    if not _port_open("127.0.0.1", 5432):
        return None

    available = run_cmd(["pg_isready", "-q"]) != "" or _port_open("127.0.0.1", 5432)
    pg_isready = run_cmd(["pg_isready"])
    connections = 0
    version = ""

    psql_out = run_cmd([
        "psql", "-U", "postgres", "-t", "-c",
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';",
    ])
    if psql_out.strip().isdigit():
        connections = int(psql_out.strip())

    ver_out = run_cmd(["psql", "-U", "postgres", "-t", "-c", "SELECT version();"])
    if ver_out:
        version = ver_out.strip()[:120]

    return {
        "type": "postgresql",
        "available": available or "accepting connections" in pg_isready.lower(),
        "connections_active": connections,
        "version": version,
        "replication": "unknown",
        "slow_queries": 0,
        "cache_hit_ratio": None,
        "disk_usage_mb": None,
    }


def check_mysql() -> dict[str, Any] | None:
    if not _port_open("127.0.0.1", 3306):
        return None

    ping = run_cmd(["mysqladmin", "ping"])
    available = "alive" in ping.lower() or _port_open("127.0.0.1", 3306)
    connections = 0
    queries_per_sec = 0.0

    status_out = run_cmd(["mysqladmin", "extended-status"])
    if status_out:
        for line in status_out.split("\n"):
            if "Threads_connected" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    connections = int(safe_float(parts[2].strip()))
            if "Queries" in line and "per second" not in line.lower():
                parts = line.split("|")
                if len(parts) >= 3 and parts[1].strip() == "Queries":
                    queries_per_sec = safe_float(parts[2].strip())

    return {
        "type": "mysql",
        "available": available,
        "connections_active": connections,
        "queries_per_sec": queries_per_sec,
        "slow_queries": 0,
        "replication": "unknown",
        "cache_hit_ratio": None,
        "disk_usage_mb": None,
    }


def check_redis() -> dict[str, Any] | None:
    if not _port_open("127.0.0.1", 6379):
        return None

    ping = run_cmd(["redis-cli", "ping"])
    available = "PONG" in ping.upper()
    connected = 0
    memory_mb = 0.0

    info = run_cmd(["redis-cli", "info"])
    if info:
        for line in info.split("\n"):
            if line.startswith("connected_clients:"):
                connected = int(safe_float(line.split(":")[1]))
            if line.startswith("used_memory:"):
                memory_mb = round(safe_float(line.split(":")[1]) / (1024 ** 2), 2)

    return {
        "type": "redis",
        "available": available,
        "connections_active": connected,
        "memory_used_mb": memory_mb,
        "replication": "unknown",
        "cache_hit_ratio": None,
    }


def collect_databases() -> list[dict[str, Any]]:
    results = []
    for checker in (check_postgresql, check_mysql, check_redis):
        item = checker()
        if item:
            results.append(item)
    return results

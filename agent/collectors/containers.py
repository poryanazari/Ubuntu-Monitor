"""Docker and Kubernetes monitoring."""

import json
from typing import Any

from collectors.common import run_cmd


def collect_docker() -> dict[str, Any] | None:
    ver = run_cmd(["docker", "version", "--format", "{{.Server.Version}}"])
    if not ver:
        return None

    containers: list[dict[str, Any]] = []
    out = run_cmd(["docker", "ps", "-a", "--format", "{{json .}}"])
    if out:
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            try:
                c = json.loads(line)
                containers.append({
                    "id": c.get("ID", "")[:12],
                    "name": c.get("Names", ""),
                    "image": c.get("Image", ""),
                    "status": c.get("Status", ""),
                    "state": c.get("State", ""),
                })
            except json.JSONDecodeError:
                continue

    images_out = run_cmd(["docker", "images", "--format", "{{json .}}"])
    image_count = 0
    if images_out:
        image_count = len([l for l in images_out.strip().split("\n") if l.strip()])

    running = sum(1 for c in containers if "running" in c.get("status", "").lower() or c.get("state") == "running")
    exited = sum(1 for c in containers if "exited" in c.get("status", "").lower() or c.get("state") == "exited")

    return {
        "version": ver.strip(),
        "container_count": len(containers),
        "running": running,
        "exited": exited,
        "paused": len(containers) - running - exited,
        "image_count": image_count,
        "containers": containers[:30],
    }


def collect_kubernetes() -> dict[str, Any] | None:
    out = run_cmd(["kubectl", "get", "nodes", "-o", "json"], timeout=15)
    if not out:
        return None

    try:
        data = json.loads(out)
        nodes = []
        for item in data.get("items", []):
            name = item.get("metadata", {}).get("name", "")
            conditions = item.get("status", {}).get("conditions", [])
            ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
            nodes.append({"name": name, "ready": ready})

        pods_out = run_cmd(["kubectl", "get", "pods", "-A", "-o", "json"], timeout=15)
        pod_count = 0
        running_pods = 0
        if pods_out:
            pods_data = json.loads(pods_out)
            items = pods_data.get("items", [])
            pod_count = len(items)
            running_pods = sum(
                1 for p in items
                if p.get("status", {}).get("phase") == "Running"
            )

        return {
            "node_count": len(nodes),
            "nodes": nodes,
            "pod_count": pod_count,
            "running_pods": running_pods,
        }
    except json.JSONDecodeError:
        return None


def collect_containers() -> dict[str, Any]:
    return {
        "docker": collect_docker(),
        "kubernetes": collect_kubernetes(),
    }

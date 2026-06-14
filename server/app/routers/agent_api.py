import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Agent, ConnectionSnapshot, LogEntry, MetricSnapshot, SoftwareItem
from app.schemas import AgentReport

router = APIRouter(prefix="/api/agent", tags=["agent"])

LOG_RETENTION_DAYS = 30


async def get_agent_by_key(agent_key: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.agent_key == agent_key))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent key")
    return agent


def _log_hash(source: str, message: str) -> str:
    return hashlib.md5(f"{source}:{message}".encode("utf-8", errors="replace")).hexdigest()


def _parse_log_ts(ts: Optional[str]) -> datetime:
    if not ts:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00").split("+")[0])
    except ValueError:
        return datetime.utcnow()


@router.post("/report")
async def receive_report(
    report: AgentReport,
    db: AsyncSession = Depends(get_db),
    x_agent_key: str = Header(..., alias="X-Agent-Key"),
):
    agent = await get_agent_by_key(x_agent_key, db)

    agent.hostname = report.hostname
    agent.ip_address = report.ip_address
    agent.os_info = report.os_info
    agent.is_online = True
    agent.last_seen = datetime.utcnow()

    extended_json = json.dumps(report.extended or {})

    metrics = MetricSnapshot(
        agent_id=agent.id,
        cpu_percent=report.metrics.cpu_percent,
        cpu_count=report.metrics.cpu_count,
        memory_total_mb=report.metrics.memory_total_mb,
        memory_used_mb=report.metrics.memory_used_mb,
        memory_percent=report.metrics.memory_percent,
        disk_total_gb=report.metrics.disk_total_gb,
        disk_used_gb=report.metrics.disk_used_gb,
        disk_percent=report.metrics.disk_percent,
        network_bytes_sent=report.metrics.network_bytes_sent,
        network_bytes_recv=report.metrics.network_bytes_recv,
        network_sent_rate=report.metrics.network_sent_rate,
        network_recv_rate=report.metrics.network_recv_rate,
        connection_count=report.metrics.connection_count,
        load_average=report.metrics.load_average,
        uptime_seconds=report.metrics.uptime_seconds,
        extended_metrics=extended_json,
    )
    db.add(metrics)

    await db.execute(delete(ConnectionSnapshot).where(ConnectionSnapshot.agent_id == agent.id))
    for conn in report.connections[:500]:
        db.add(
            ConnectionSnapshot(
                agent_id=agent.id,
                local_addr=conn.local_addr,
                remote_addr=conn.remote_addr,
                status=conn.status,
                pid=conn.pid,
                process_name=conn.process_name,
            )
        )

    await db.execute(delete(SoftwareItem).where(SoftwareItem.agent_id == agent.id))
    for item in report.software:
        db.add(
            SoftwareItem(
                agent_id=agent.id,
                name=item.name,
                version=item.version,
                category=item.category,
                status=item.status,
                details=item.details,
            )
        )

    existing_hashes = set()
    if report.logs:
        hash_result = await db.execute(
            select(LogEntry.content_hash).where(LogEntry.agent_id == agent.id).limit(5000)
        )
        existing_hashes = set(hash_result.scalars().all())

        for log in report.logs[:400]:
            h = _log_hash(log.source, log.message)
            if h in existing_hashes:
                continue
            existing_hashes.add(h)
            db.add(
                LogEntry(
                    agent_id=agent.id,
                    timestamp=_parse_log_ts(log.timestamp),
                    source=log.source[:64],
                    level=log.level[:16],
                    message=log.message[:4000],
                    content_hash=h,
                )
            )

    cutoff = datetime.utcnow() - timedelta(days=LOG_RETENTION_DAYS)
    await db.execute(delete(LogEntry).where(LogEntry.agent_id == agent.id, LogEntry.created_at < cutoff))

    await db.commit()

    from app.services.alerts import evaluate_metrics_for_agent, evaluate_online_agent
    await evaluate_metrics_for_agent(db, agent.id, metrics)
    await evaluate_online_agent(db, agent)
    await db.commit()

    return {"ok": True, "agent_id": agent.id}

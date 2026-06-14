import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Agent, ConnectionSnapshot, LogEntry, MetricSnapshot, SoftwareItem
from app.schemas import (
    AgentCreate,
    AgentResponse,
    ConnectionResponse,
    DashboardSummary,
    LogResponse,
    MetricSnapshotResponse,
    SearchHit,
    SearchResponse,
    SoftwareResponse,
)


def _metric_to_response(m: MetricSnapshot) -> MetricSnapshotResponse:
    extended = {}
    if m.extended_metrics:
        try:
            extended = json.loads(m.extended_metrics)
        except json.JSONDecodeError:
            extended = {}
    return MetricSnapshotResponse(
        id=m.id,
        agent_id=m.agent_id,
        timestamp=m.timestamp,
        cpu_percent=m.cpu_percent,
        memory_percent=m.memory_percent,
        memory_used_mb=m.memory_used_mb,
        memory_total_mb=m.memory_total_mb,
        disk_percent=m.disk_percent,
        network_sent_rate=m.network_sent_rate,
        network_recv_rate=m.network_recv_rate,
        connection_count=m.connection_count,
        load_average=m.load_average,
        uptime_seconds=m.uptime_seconds,
        extended_metrics=extended,
    )


router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    agents_result = await db.execute(select(Agent))
    agents = agents_result.scalars().all()
    online = sum(1 for a in agents if a.is_online)

    latest_metrics = []
    for agent in agents:
        metric_result = await db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.agent_id == agent.id)
            .order_by(MetricSnapshot.timestamp.desc())
            .limit(1)
        )
        metric = metric_result.scalar_one_or_none()
        if metric:
            latest_metrics.append(metric)

    avg_cpu = sum(m.cpu_percent for m in latest_metrics) / len(latest_metrics) if latest_metrics else 0
    avg_memory = sum(m.memory_percent for m in latest_metrics) / len(latest_metrics) if latest_metrics else 0
    total_connections = sum(m.connection_count for m in latest_metrics)

    return DashboardSummary(
        total_agents=len(agents),
        online_agents=online,
        total_connections=total_connections,
        avg_cpu=round(avg_cpu, 2),
        avg_memory=round(avg_memory, 2),
    )


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.name))
    return result.scalars().all()


@router.post("/agents", response_model=AgentResponse)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent_key = secrets.token_urlsafe(32)
    agent = Agent(name=payload.name, hostname=payload.hostname or payload.name, agent_key=agent_key)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
    return {"ok": True}


@router.get("/agents/{agent_id}/metrics", response_model=list[MetricSnapshotResponse])
async def agent_metrics(
    agent_id: int,
    hours: int = Query(24, ge=1, le=720),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    if from_ts and to_ts:
        since, until = from_ts, to_ts
    else:
        since = datetime.utcnow() - timedelta(hours=hours)
        until = datetime.utcnow()

    result = await db.execute(
        select(MetricSnapshot)
        .where(
            MetricSnapshot.agent_id == agent_id,
            MetricSnapshot.timestamp >= since,
            MetricSnapshot.timestamp <= until,
        )
        .order_by(MetricSnapshot.timestamp.asc())
    )
    return [_metric_to_response(m) for m in result.scalars().all()]


@router.get("/agents/{agent_id}/metrics/latest", response_model=MetricSnapshotResponse)
async def agent_metrics_latest(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.agent_id == agent_id)
        .order_by(MetricSnapshot.timestamp.desc())
        .limit(1)
    )
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(status_code=404, detail="No metrics found")
    return _metric_to_response(metric)


@router.get("/agents/{agent_id}/software", response_model=list[SoftwareResponse])
async def agent_software(
    agent_id: int,
    q: str = Query("", min_length=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SoftwareItem).where(SoftwareItem.agent_id == agent_id)
    if q:
        stmt = stmt.where(
            or_(
                SoftwareItem.name.ilike(f"%{q}%"),
                SoftwareItem.details.ilike(f"%{q}%"),
            )
        )
    result = await db.execute(stmt.order_by(SoftwareItem.name))
    return result.scalars().all()


@router.get("/agents/{agent_id}/connections", response_model=list[ConnectionResponse])
async def agent_connections(
    agent_id: int,
    q: str = Query("", min_length=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConnectionSnapshot).where(ConnectionSnapshot.agent_id == agent_id)
    if q:
        stmt = stmt.where(
            or_(
                ConnectionSnapshot.local_addr.ilike(f"%{q}%"),
                ConnectionSnapshot.remote_addr.ilike(f"%{q}%"),
                ConnectionSnapshot.process_name.ilike(f"%{q}%"),
                ConnectionSnapshot.status.ilike(f"%{q}%"),
            )
        )
    result = await db.execute(stmt.order_by(ConnectionSnapshot.timestamp.desc()).limit(500))
    return result.scalars().all()


@router.get("/agents/{agent_id}/logs", response_model=list[LogResponse])
async def agent_logs(
    agent_id: int,
    hours: int = Query(24, ge=1, le=720),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    q: str = Query("", min_length=0),
    level: str = Query("", min_length=0),
    source: str = Query("", min_length=0),
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    if from_ts and to_ts:
        since, until = from_ts, to_ts
    else:
        since = datetime.utcnow() - timedelta(hours=hours)
        until = datetime.utcnow()

    stmt = select(LogEntry).where(
        LogEntry.agent_id == agent_id,
        LogEntry.timestamp >= since,
        LogEntry.timestamp <= until,
    )
    if q:
        stmt = stmt.where(LogEntry.message.ilike(f"%{q}%"))
    if level:
        stmt = stmt.where(LogEntry.level == level)
    if source:
        stmt = stmt.where(LogEntry.source.ilike(f"%{source}%"))

    result = await db.execute(stmt.order_by(LogEntry.timestamp.desc()).limit(limit))
    return result.scalars().all()


@router.get("/search", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1),
    agent_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    term = f"%{q}%"
    hits: list[SearchHit] = []

    agents_stmt = select(Agent)
    if agent_id:
        agents_stmt = agents_stmt.where(Agent.id == agent_id)
    agents_result = await db.execute(agents_stmt)
    agents = {a.id: a for a in agents_result.scalars().all()}

    for aid, agent in agents.items():
        if q.lower() in agent.name.lower() or q.lower() in (agent.hostname or "").lower():
            hits.append(SearchHit(
                type="agent", id=agent.id, agent_id=agent.id, agent_name=agent.name,
                title=agent.name, subtitle=agent.ip_address or agent.hostname,
                timestamp=agent.last_seen,
            ))

    sw_stmt = select(SoftwareItem)
    if agent_id:
        sw_stmt = sw_stmt.where(SoftwareItem.agent_id == agent_id)
    sw_stmt = sw_stmt.where(or_(SoftwareItem.name.ilike(term), SoftwareItem.details.ilike(term))).limit(30)
    for item in (await db.execute(sw_stmt)).scalars():
        agent = agents.get(item.agent_id)
        hits.append(SearchHit(
            type="software", id=item.id, agent_id=item.agent_id,
            agent_name=agent.name if agent else "",
            title=item.name, subtitle=item.category,
            timestamp=item.last_seen,
        ))

    conn_stmt = select(ConnectionSnapshot)
    if agent_id:
        conn_stmt = conn_stmt.where(ConnectionSnapshot.agent_id == agent_id)
    conn_stmt = conn_stmt.where(
        or_(
            ConnectionSnapshot.local_addr.ilike(term),
            ConnectionSnapshot.remote_addr.ilike(term),
            ConnectionSnapshot.process_name.ilike(term),
        )
    ).limit(30)
    for item in (await db.execute(conn_stmt)).scalars():
        agent = agents.get(item.agent_id)
        hits.append(SearchHit(
            type="connection", id=item.id, agent_id=item.agent_id,
            agent_name=agent.name if agent else "",
            title=item.local_addr, subtitle=f"{item.status} · {item.process_name}",
            timestamp=item.timestamp,
        ))

    log_stmt = select(LogEntry)
    if agent_id:
        log_stmt = log_stmt.where(LogEntry.agent_id == agent_id)
    log_stmt = log_stmt.where(LogEntry.message.ilike(term)).order_by(LogEntry.timestamp.desc()).limit(50)
    for item in (await db.execute(log_stmt)).scalars():
        agent = agents.get(item.agent_id)
        hits.append(SearchHit(
            type="log", id=item.id, agent_id=item.agent_id,
            agent_name=agent.name if agent else "",
            title=item.message[:120], subtitle=f"{item.source} · {item.level}",
            timestamp=item.timestamp,
        ))

    return SearchResponse(query=q, total=len(hits), results=hits[:100])

"""Alert rule evaluation and Bale notifications."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Agent, AlertRule, AlertState, MetricSnapshot, NotificationChannel, NotificationLog
from app.services.bale import BaleClient

METRIC_LABELS = {
    "cpu_percent": "CPU %",
    "memory_percent": "RAM %",
    "disk_percent": "Disk %",
    "network_sent_rate": "Network upload (B/s)",
    "network_recv_rate": "Network download (B/s)",
    "connection_count": "Connections",
    "load_average": "Load average",
    "agent_offline": "Agent offline (minutes)",
}

OPERATORS = {
    "gt": lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "lt": lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "eq": lambda v, t: v == t,
}


def metric_value_from_snapshot(metric: str, snap: MetricSnapshot) -> float | None:
    mapping = {
        "cpu_percent": snap.cpu_percent,
        "memory_percent": snap.memory_percent,
        "disk_percent": snap.disk_percent,
        "network_sent_rate": snap.network_sent_rate,
        "network_recv_rate": snap.network_recv_rate,
        "connection_count": float(snap.connection_count),
        "load_average": snap.load_average,
    }
    if metric not in mapping:
        return None
    return float(mapping[metric])


def check_condition(value: float, operator: str, threshold: float) -> bool:
    fn = OPERATORS.get(operator, OPERATORS["gt"])
    return fn(value, threshold)


def format_alert_message(
    event_type: str,
    rule: AlertRule,
    agent: Agent,
    value: float,
    severity: str,
) -> str:
    label = METRIC_LABELS.get(rule.metric, rule.metric)
    icon = "🔴" if severity == "critical" else "🟠" if event_type == "trigger" else "🟢"
    action = "ALERT" if event_type == "trigger" else "RECOVERED" if event_type == "recovery" else "TEST"
    return (
        f"{icon} Ubuntu Monitor — {action}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Rule: {rule.name}\n"
        f"Server: {agent.name} ({agent.ip_address or agent.hostname})\n"
        f"Metric: {label}\n"
        f"Value: {value}\n"
        f"Threshold: {rule.operator} {rule.threshold}\n"
        f"Severity: {severity}\n"
        f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )


async def send_to_channel(
    db: AsyncSession,
    channel: NotificationChannel,
    message: str,
    rule_id: int | None = None,
    agent_id: int | None = None,
    event_type: str = "manual",
    severity: str = "info",
) -> bool:
    client = BaleClient()
    success = False
    error = ""
    try:
        await client.send_message(channel.chat_id, message)
        success = True
    except Exception as e:
        error = str(e)[:500]
        message = f"{message}\n\n(send failed: {error})"

    db.add(
        NotificationLog(
            channel_id=channel.id,
            rule_id=rule_id,
            agent_id=agent_id,
            event_type=event_type,
            severity=severity,
            message=message[:4000],
            success=success,
        )
    )
    return success


async def _get_or_create_state(db: AsyncSession, rule_id: int, agent_id: int) -> AlertState:
    result = await db.execute(
        select(AlertState).where(AlertState.rule_id == rule_id, AlertState.agent_id == agent_id)
    )
    state = result.scalar_one_or_none()
    if not state:
        state = AlertState(rule_id=rule_id, agent_id=agent_id)
        db.add(state)
        await db.flush()
    return state


async def evaluate_rule_for_agent(
    db: AsyncSession,
    rule: AlertRule,
    agent: Agent,
    value: float,
    channel: NotificationChannel,
) -> None:
    if not rule.enabled or not channel.enabled:
        return

    firing = check_condition(value, rule.operator, rule.threshold)
    state = await _get_or_create_state(db, rule.id, agent.id)
    state.last_value = value
    now = datetime.utcnow()
    cooldown = timedelta(minutes=rule.cooldown_minutes)

    if firing:
        should_notify = False
        if not state.is_firing:
            state.is_firing = True
            state.fired_at = now
            should_notify = True
        elif state.last_notified_at and (now - state.last_notified_at) >= cooldown:
            should_notify = True

        if should_notify:
            msg = format_alert_message("trigger", rule, agent, value, rule.severity)
            await send_to_channel(
                db, channel, msg, rule_id=rule.id, agent_id=agent.id,
                event_type="trigger", severity=rule.severity,
            )
            state.last_notified_at = now
    elif state.is_firing:
        state.is_firing = False
        state.fired_at = None
        if rule.notify_recovery:
            msg = format_alert_message("recovery", rule, agent, value, "info")
            await send_to_channel(
                db, channel, msg, rule_id=rule.id, agent_id=agent.id,
                event_type="recovery", severity="info",
            )


async def evaluate_metrics_for_agent(db: AsyncSession, agent_id: int, snapshot: MetricSnapshot) -> None:
    rules_result = await db.execute(
        select(AlertRule)
        .options(selectinload(AlertRule.channel))
        .where(AlertRule.enabled.is_(True))
    )
    rules = rules_result.scalars().all()
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return

    for rule in rules:
        if rule.metric == "agent_offline":
            continue
        if rule.agent_id is not None and rule.agent_id != agent_id:
            continue
        if not rule.channel or not rule.channel.enabled:
            continue
        value = metric_value_from_snapshot(rule.metric, snapshot)
        if value is None:
            continue
        await evaluate_rule_for_agent(db, rule, agent, value, rule.channel)


async def evaluate_offline_agents(db: AsyncSession) -> None:
    rules_result = await db.execute(
        select(AlertRule)
        .options(selectinload(AlertRule.channel))
        .where(AlertRule.enabled.is_(True), AlertRule.metric == "agent_offline")
    )
    offline_rules = rules_result.scalars().all()
    if not offline_rules:
        return

    agents_result = await db.execute(select(Agent))
    agents = agents_result.scalars().all()
    now = datetime.utcnow()
    offline_threshold = timedelta(minutes=settings.agent_offline_minutes)

    for agent in agents:
        minutes_offline = 0.0
        is_offline = False
        if not agent.last_seen:
            is_offline = True
            minutes_offline = float(settings.agent_offline_minutes)
        elif (now - agent.last_seen) > offline_threshold:
            is_offline = True
            minutes_offline = (now - agent.last_seen).total_seconds() / 60

        for rule in offline_rules:
            if rule.agent_id is not None and rule.agent_id != agent.id:
                continue
            if not rule.channel or not rule.channel.enabled:
                continue
            await evaluate_rule_for_agent(
                db, rule, agent,
                minutes_offline if is_offline else 0.0,
                rule.channel,
            )

        if not is_offline and not agent.is_online:
            agent.is_online = False

async def evaluate_online_agent(db: AsyncSession, agent: Agent) -> None:
    """Clear offline alerts when agent reports."""
    rules_result = await db.execute(
        select(AlertRule)
        .options(selectinload(AlertRule.channel))
        .where(AlertRule.enabled.is_(True), AlertRule.metric == "agent_offline")
    )
    for rule in rules_result.scalars().all():
        if rule.agent_id is not None and rule.agent_id != agent.id:
            continue
        if not rule.channel or not rule.channel.enabled:
            continue
        await evaluate_rule_for_agent(db, rule, agent, 0.0, rule.channel)


async def discover_bale_chats() -> list[dict[str, Any]]:
    client = BaleClient()
    updates = await client.get_updates(limit=50)
    seen: dict[str, dict[str, Any]] = {}
    for upd in updates:
        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat", {})
        cid = chat.get("id")
        if cid is None:
            continue
        username = chat.get("username")
        # Prefer @username for Bale groups when available
        send_id = f"@{username}" if username else str(cid)
        key = send_id
        if key not in seen:
            seen[key] = {
                "chat_id": send_id,
                "numeric_id": str(cid),
                "title": chat.get("title") or chat.get("first_name") or username or str(cid),
                "type": chat.get("type", "unknown"),
            }
    return list(seen.values())

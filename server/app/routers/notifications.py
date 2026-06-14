"""Notification channels and alert rules API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import AlertRule, NotificationChannel, NotificationLog
from app.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    BaleChatInfo,
    BaleTestRequest,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationLogResponse,
)
from app.services.alerts import METRIC_LABELS, discover_bale_chats, send_to_channel
from app.services.bale import BaleClient, normalize_chat_id
from app.config import settings

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)])


@router.get("/metrics")
async def list_metric_types():
    return [{"key": k, "label": v} for k, v in METRIC_LABELS.items()]


@router.get("/bale/status")
async def bale_status():
    configured = bool(settings.bale_bot_token.strip())
    if not configured:
        return {"configured": False, "bot": None, "env_file": str(settings.model_config.get("env_file", ""))}
    try:
        bot = await BaleClient().get_me()
        return {"configured": True, "connected": True, "bot": bot}
    except Exception as e:
        return {"configured": True, "connected": False, "bot": None, "error": str(e)}


@router.get("/bale/chats", response_model=list[BaleChatInfo])
async def bale_discover_chats():
    try:
        return await discover_bale_chats()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bale/test")
async def bale_test(payload: BaleTestRequest):
    if not payload.chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")
    try:
        await BaleClient().send_message(
            payload.chat_id,
            "✅ Ubuntu Monitor test — Bale notifications are working.",
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/channels", response_model=list[NotificationChannelResponse])
async def list_channels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationChannel).order_by(NotificationChannel.name))
    return result.scalars().all()


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_channel(payload: NotificationChannelCreate, db: AsyncSession = Depends(get_db)):
    ch = NotificationChannel(
        name=payload.name,
        channel_type=payload.channel_type,
        chat_id=normalize_chat_id(payload.chat_id),
        enabled=payload.enabled,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(channel_id: int, payload: NotificationChannelCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    ch.name = payload.name
    ch.chat_id = normalize_chat_id(payload.chat_id)
    ch.enabled = payload.enabled
    await db.commit()
    await db.refresh(ch)
    return ch


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.execute(
        delete(NotificationLog).where(NotificationLog.channel_id == channel_id)
    )
    await db.delete(ch)
    await db.commit()
    return {"ok": True}


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AlertRule).options(selectinload(AlertRule.channel)).order_by(AlertRule.name)
    )
    rules = result.scalars().all()
    out = []
    for r in rules:
        out.append(AlertRuleResponse(
            id=r.id, name=r.name, agent_id=r.agent_id, channel_id=r.channel_id,
            metric=r.metric, operator=r.operator, threshold=r.threshold,
            severity=r.severity, cooldown_minutes=r.cooldown_minutes,
            enabled=r.enabled, notify_recovery=r.notify_recovery,
            created_at=r.created_at,
            channel_name=r.channel.name if r.channel else "",
        ))
    return out


@router.post("/rules", response_model=AlertRuleResponse)
async def create_rule(payload: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    ch = await db.get(NotificationChannel, rule.channel_id)
    return AlertRuleResponse(
        id=rule.id, name=rule.name, agent_id=rule.agent_id, channel_id=rule.channel_id,
        metric=rule.metric, operator=rule.operator, threshold=rule.threshold,
        severity=rule.severity, cooldown_minutes=rule.cooldown_minutes,
        enabled=rule.enabled, notify_recovery=rule.notify_recovery,
        created_at=rule.created_at, channel_name=ch.name if ch else "",
    )


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(rule_id: int, payload: AlertRuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    ch = await db.get(NotificationChannel, rule.channel_id)
    return AlertRuleResponse(
        id=rule.id, name=rule.name, agent_id=rule.agent_id, channel_id=rule.channel_id,
        metric=rule.metric, operator=rule.operator, threshold=rule.threshold,
        severity=rule.severity, cooldown_minutes=rule.cooldown_minutes,
        enabled=rule.enabled, notify_recovery=rule.notify_recovery,
        created_at=rule.created_at, channel_name=ch.name if ch else "",
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.execute(
        update(NotificationLog).where(NotificationLog.rule_id == rule_id).values(rule_id=None)
    )
    await db.delete(rule)
    await db.commit()
    return {"ok": True}


@router.get("/logs", response_model=list[NotificationLogResponse])
async def notification_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
    )
    return result.scalars().all()

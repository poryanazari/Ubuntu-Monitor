from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    agent_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    os_info: Mapped[str] = mapped_column(String(255), default="")
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    metrics: Mapped[list["MetricSnapshot"]] = relationship(back_populates="agent")
    software: Mapped[list["SoftwareItem"]] = relationship(back_populates="agent")
    connections: Mapped[list["ConnectionSnapshot"]] = relationship(back_populates="agent")
    logs: Mapped[list["LogEntry"]] = relationship(back_populates="agent")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    cpu_percent: Mapped[float] = mapped_column(Float, default=0)
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_total_mb: Mapped[float] = mapped_column(Float, default=0)
    memory_used_mb: Mapped[float] = mapped_column(Float, default=0)
    memory_percent: Mapped[float] = mapped_column(Float, default=0)
    disk_total_gb: Mapped[float] = mapped_column(Float, default=0)
    disk_used_gb: Mapped[float] = mapped_column(Float, default=0)
    disk_percent: Mapped[float] = mapped_column(Float, default=0)
    network_bytes_sent: Mapped[float] = mapped_column(Float, default=0)
    network_bytes_recv: Mapped[float] = mapped_column(Float, default=0)
    network_sent_rate: Mapped[float] = mapped_column(Float, default=0)
    network_recv_rate: Mapped[float] = mapped_column(Float, default=0)
    connection_count: Mapped[int] = mapped_column(Integer, default=0)
    load_average: Mapped[float] = mapped_column(Float, default=0)
    uptime_seconds: Mapped[float] = mapped_column(Float, default=0)
    extended_metrics: Mapped[str] = mapped_column(Text, default="{}")

    agent: Mapped["Agent"] = relationship(back_populates="metrics")


class ConnectionSnapshot(Base):
    __tablename__ = "connection_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    local_addr: Mapped[str] = mapped_column(String(64))
    remote_addr: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32))
    pid: Mapped[int] = mapped_column(Integer, default=0)
    process_name: Mapped[str] = mapped_column(String(128), default="")

    agent: Mapped["Agent"] = relationship(back_populates="connections")


class SoftwareItem(Base):
    __tablename__ = "software_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(128), default="")
    category: Mapped[str] = mapped_column(String(64), default="package")
    status: Mapped[str] = mapped_column(String(32), default="installed")
    details: Mapped[str] = mapped_column(Text, default="")
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="software")


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source: Mapped[str] = mapped_column(String(64), default="system", index=True)
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    message: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Agent"] = relationship(back_populates="logs")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    channel_type: Mapped[str] = mapped_column(String(32), default="bale")
    chat_id: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rules: Mapped[list["AlertRule"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("notification_channels.id"), index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    operator: Mapped[str] = mapped_column(String(8), default="gt")
    threshold: Mapped[float] = mapped_column(Float, default=0)
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_recovery: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["NotificationChannel"] = relationship(back_populates="rules")
    states: Mapped[list["AlertState"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertState(Base):
    __tablename__ = "alert_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    is_firing: Mapped[bool] = mapped_column(Boolean, default=False)
    last_value: Mapped[float] = mapped_column(Float, default=0)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rule: Mapped["AlertRule"] = relationship(back_populates="states")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("notification_channels.id"), index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id"), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

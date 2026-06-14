from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    name: str
    hostname: str = ""


class AgentResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: str
    agent_key: str
    os_info: str
    is_online: bool
    last_seen: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class MetricPayload(BaseModel):
    cpu_percent: float = 0
    cpu_count: int = 0
    memory_total_mb: float = 0
    memory_used_mb: float = 0
    memory_percent: float = 0
    disk_total_gb: float = 0
    disk_used_gb: float = 0
    disk_percent: float = 0
    network_bytes_sent: float = 0
    network_bytes_recv: float = 0
    network_sent_rate: float = 0
    network_recv_rate: float = 0
    connection_count: int = 0
    load_average: float = 0
    uptime_seconds: float = 0


class ConnectionItem(BaseModel):
    local_addr: str
    remote_addr: str = ""
    status: str
    pid: int = 0
    process_name: str = ""


class SoftwareItemPayload(BaseModel):
    name: str
    version: str = ""
    category: str = "package"
    status: str = "installed"
    details: str = ""


class LogItemPayload(BaseModel):
    source: str = "system"
    level: str = "info"
    message: str
    timestamp: Optional[str] = None


class AgentReport(BaseModel):
    hostname: str
    ip_address: str = ""
    os_info: str = ""
    metrics: MetricPayload
    extended: dict[str, Any] = Field(default_factory=dict)
    connections: list[ConnectionItem] = Field(default_factory=list)
    software: list[SoftwareItemPayload] = Field(default_factory=list)
    logs: list[LogItemPayload] = Field(default_factory=list)


class MetricSnapshotResponse(BaseModel):
    id: int
    agent_id: int
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    network_sent_rate: float
    network_recv_rate: float
    connection_count: int
    load_average: float
    uptime_seconds: float
    extended_metrics: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class SoftwareResponse(BaseModel):
    id: int
    name: str
    version: str
    category: str
    status: str
    details: str
    last_seen: datetime

    class Config:
        from_attributes = True


class ConnectionResponse(BaseModel):
    id: int
    local_addr: str
    remote_addr: str
    status: str
    pid: int
    process_name: str
    timestamp: datetime

    class Config:
        from_attributes = True


class LogResponse(BaseModel):
    id: int
    agent_id: int
    timestamp: datetime
    source: str
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class SearchHit(BaseModel):
    type: str
    id: int
    agent_id: int
    agent_name: str
    title: str
    subtitle: str
    timestamp: Optional[datetime] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchHit]


class DashboardSummary(BaseModel):
    total_agents: int
    online_agents: int
    total_connections: int
    avg_cpu: float
    avg_memory: float


class NotificationChannelCreate(BaseModel):
    name: str
    channel_type: str = "bale"
    chat_id: str
    enabled: bool = True


class NotificationChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str
    chat_id: str
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertRuleCreate(BaseModel):
    name: str
    agent_id: Optional[int] = None
    channel_id: int
    metric: str
    operator: str = "gt"
    threshold: float = 0
    severity: str = "warning"
    cooldown_minutes: int = 5
    enabled: bool = True
    notify_recovery: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[int] = None
    channel_id: Optional[int] = None
    metric: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    enabled: Optional[bool] = None
    notify_recovery: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    agent_id: Optional[int]
    channel_id: int
    metric: str
    operator: str
    threshold: float
    severity: str
    cooldown_minutes: int
    enabled: bool
    notify_recovery: bool
    created_at: datetime
    channel_name: str = ""

    class Config:
        from_attributes = True


class NotificationLogResponse(BaseModel):
    id: int
    channel_id: int
    rule_id: Optional[int]
    agent_id: Optional[int]
    event_type: str
    severity: str
    message: str
    success: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BaleChatInfo(BaseModel):
    chat_id: str
    title: str
    type: str


class BaleTestRequest(BaseModel):
    chat_id: str

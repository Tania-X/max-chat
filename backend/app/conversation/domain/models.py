from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatSession:
    id: str
    user_id: str
    title: str = "新会话"
    model_config_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    id: str
    session_id: str
    user_id: str
    role: str  # user | assistant
    content: str
    tool_events: list[dict] = field(default_factory=list)
    trace_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

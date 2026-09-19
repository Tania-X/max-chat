from dataclasses import dataclass, field
from datetime import datetime

from app.shared.clock import utcnow


@dataclass
class Memory:
    id: str
    user_id: str
    content: str
    category: str = "general"  # preference | fact | habit | general
    source_session_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class UserProfile:
    user_id: str
    data: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utcnow)

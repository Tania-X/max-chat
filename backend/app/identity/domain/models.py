from dataclasses import dataclass, field
from datetime import datetime

from app.shared.clock import utcnow


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    display_name: str = ""
    created_at: datetime = field(default_factory=utcnow)

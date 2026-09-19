from dataclasses import dataclass, field
from datetime import datetime

from app.shared.clock import utcnow


@dataclass
class Capability:
    id: str
    user_id: str
    type: str  # plugin | skill | mcp
    name: str
    description: str = ""
    enabled: bool = True
    config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)

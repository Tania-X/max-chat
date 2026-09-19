from dataclasses import dataclass, field
from datetime import datetime

from app.shared.clock import utcnow


@dataclass
class ModelConfig:
    id: str
    user_id: str
    provider: str  # gemini | openai | anthropic | deepseek | ...
    model_name: str
    api_key: str = ""
    base_url: str = ""
    label: str = ""
    is_default: bool = False
    created_at: datetime = field(default_factory=utcnow)

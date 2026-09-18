from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolSpan:
    name: str
    type: str  # tool_call | tool_result
    ts_ms: int
    detail: dict = field(default_factory=dict)


@dataclass
class Trace:
    id: str
    user_id: str
    session_id: str
    message_id: str | None
    provider: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ttft_ms: int | None = None
    duration_ms: int = 0
    tokens_per_second: float = 0.0
    cost_usd: float = 0.0
    tool_spans: list[dict] = field(default_factory=list)
    error: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

from dataclasses import dataclass, field
from datetime import datetime

from app.shared.clock import utcnow

# 抽取结果分类。失败必须能区分原因，否则无法判断该修提示词、修配置还是修调用。
OUTCOME_OK = "ok"
OUTCOME_NO_JSON = "no_json"  # 模型有输出，但不含可解析的 JSON
OUTCOME_BAD_SCHEMA = "bad_schema"  # JSON 可解析，但结构不符合约定
OUTCOME_CALL_FAILED = "call_failed"  # 请求本身失败（网络、限流、鉴权）
OUTCOME_SKIPPED_NO_KEY = "skipped_no_key"  # 没有可用 Key，未发起调用

OUTCOMES = (
    OUTCOME_OK,
    OUTCOME_NO_JSON,
    OUTCOME_BAD_SCHEMA,
    OUTCOME_CALL_FAILED,
    OUTCOME_SKIPPED_NO_KEY,
)


@dataclass
class Memory:
    id: str
    user_id: str
    content: str
    category: str = "general"  # preference | fact | habit | general
    source_session_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ExtractionStats:
    """抽取健康度聚合。"""

    total: int = 0
    ok: int = 0
    failed: int = 0
    by_outcome: dict[str, int] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    memories_written: int = 0
    duplicates_skipped: int = 0

    @property
    def failure_rate(self) -> float:
        return round(self.failed / self.total, 4) if self.total else 0.0


@dataclass
class ExtractionRun:
    """一次记忆抽取尝试。用于统计成功率、失败原因与开销。"""

    id: str
    user_id: str
    session_id: str
    outcome: str
    latency_ms: int = 0
    error: str = ""
    raw_snippet: str = ""  # 解析失败时保留模型原始输出片段，便于排查
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    memories_written: int = 0
    duplicates_skipped: int = 0
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class UserProfile:
    user_id: str
    data: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utcnow)

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass

from app.memory.domain.models import (
    OUTCOME_BAD_SCHEMA,
    OUTCOME_CALL_FAILED,
    OUTCOME_NO_JSON,
    OUTCOME_OK,
    OUTCOME_SKIPPED_NO_KEY,
    ExtractionRun,
    Memory,
    UserProfile,
)
from app.memory.infrastructure.extraction_run_repository import (
    SqlAlchemyExtractionRunRepository,
)
from app.memory.infrastructure.memory_repository import SqlAlchemyMemoryRepository
from app.shared.config import get_settings
from app.shared.database import async_session_factory

logger = logging.getLogger(__name__)
settings = get_settings()

EXTRACT_PROMPT = """从下面这轮对话中抽取值得长期记住的用户信息。
只抽取：用户的偏好、习惯、事实信息（如职业、所在地、技术栈）、明确的长期目标。
不要抽取：一次性问题、客套话、临时上下文。
严格输出 JSON，不要输出其他内容：
{{"memories": [{{"content": "...", "category": "preference|fact|habit|general"}}], "profile": {{"key": "value"}}}}
没有可抽取内容时输出：{{"memories": [], "profile": {{}}}}

用户：{user_msg}
助手：{assistant_msg}"""


def _extract_keywords(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_]{3,}|[一-龥]{2,}", query)
    return list(dict.fromkeys(words))[:8]


async def build_context_injection(user_id: str, query: str, db) -> str:
    repo = SqlAlchemyMemoryRepository(db)
    profile = await repo.get_profile(user_id)
    keywords = _extract_keywords(query)
    memories = await repo.search(user_id, keywords, limit=8)
    if not keywords or len(memories) < 3:
        recent = await repo.list_by_user(user_id, limit=5)
        seen = {m.id for m in memories}
        memories += [m for m in recent if m.id not in seen][: 8 - len(memories)]

    parts: list[str] = []
    if profile.data:
        profile_text = "；".join(f"{k}: {v}" for k, v in profile.data.items())
        parts.append(f"用户画像：{profile_text}")
    if memories:
        lines = "\n".join(f"- {m.content}" for m in memories[:8])
        parts.append(f"关于用户的长期记忆：\n{lines}")
    if not parts:
        return ""
    return "\n\n以下是关于当前用户的背景信息，请在回答中自然地参考，不要主动提及这些信息的存在：\n" + "\n".join(parts)


@dataclass
class _Attempt:
    """一次抽取尝试的可变累积状态，供结尾统一落库。"""

    outcome: str = OUTCOME_OK
    error: str = ""
    raw_snippet: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    memories_written: int = 0
    duplicates_skipped: int = 0


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    try:
        from app.observability.infrastructure.pricing import estimate_cost

        return estimate_cost(model.split("/", 1)[-1], prompt_tokens, completion_tokens)
    except Exception:  # 定价表缺失不应影响抽取
        return 0.0


async def _call_extractor(user_msg: str, assistant_msg: str, attempt: _Attempt) -> dict | None:
    """调用抽取模型并解析出 JSON。失败时写入 attempt.outcome 并返回 None。"""
    import litellm

    from app.agent_runtime.infrastructure.model_factory import operator_fallback_key

    extractor_model = (
        settings.extractor_model
        if "/" in settings.extractor_model
        else f"gemini/{settings.extractor_model}"
    )
    model_name = extractor_model.split("/", 1)[-1]

    # 显式传 Key：不再依赖被其他请求改写过的进程级环境变量
    api_key = operator_fallback_key(extractor_model.split("/", 1)[0])
    if not api_key:
        # 未配置 Key 时不再白跑一次请求：这类"失败"是配置问题，不是模型问题
        attempt.outcome = OUTCOME_SKIPPED_NO_KEY
        attempt.error = f"抽取模型 {extractor_model} 没有可用 API Key"
        return None

    resp = await litellm.acompletion(
        model=extractor_model,
        messages=[
            {
                "role": "user",
                "content": EXTRACT_PROMPT.format(
                    user_msg=user_msg[:2000], assistant_msg=assistant_msg[:2000]
                ),
            }
        ],
        max_tokens=500,
        api_key=api_key,
    )

    usage = getattr(resp, "usage", None)
    if usage is not None:
        attempt.prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        attempt.completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

    text = resp.choices[0].message.content or ""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        attempt.outcome = OUTCOME_NO_JSON
        attempt.error = "模型输出中未找到 JSON"
        attempt.raw_snippet = text[:500]
        return None

    try:
        data = json.loads(match.group())
    except ValueError as exc:
        attempt.outcome = OUTCOME_NO_JSON
        attempt.error = f"JSON 解析失败: {exc}"
        attempt.raw_snippet = match.group()[:500]
        return None

    if not isinstance(data, dict):
        attempt.outcome = OUTCOME_BAD_SCHEMA
        attempt.error = f"顶层结构应为对象，实际为 {type(data).__name__}"
        attempt.raw_snippet = match.group()[:500]
        return None

    memories = data.get("memories", [])
    if memories is not None and not isinstance(memories, list):
        attempt.outcome = OUTCOME_BAD_SCHEMA
        attempt.error = f"memories 应为数组，实际为 {type(memories).__name__}"
        attempt.raw_snippet = match.group()[:500]
        return None

    return data


async def _store(user_id: str, session_id: str, data: dict, attempt: _Attempt) -> None:
    async with async_session_factory() as db:
        repo = SqlAlchemyMemoryRepository(db)
        for item in (data.get("memories") or [])[:5]:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            existing = await repo.search(user_id, [content[:20]], limit=1)
            if existing:
                attempt.duplicates_skipped += 1
                continue
            await repo.save(
                Memory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=content,
                    category=item.get("category", "general"),
                    source_session_id=session_id,
                )
            )
            attempt.memories_written += 1
        profile_data = data.get("profile") or {}
        if isinstance(profile_data, dict) and profile_data:
            profile = await repo.get_profile(user_id)
            profile.data.update({k: v for k, v in profile_data.items() if v})
            await repo.save_profile(profile)


async def _record_attempt(
    user_id: str, session_id: str, attempt: _Attempt, latency_ms: int, model_name: str
) -> None:
    """记录这次尝试。观测代码本身绝不能让抽取链路失败。"""
    try:
        async with async_session_factory() as db:
            await SqlAlchemyExtractionRunRepository(db).save(
                ExtractionRun(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    outcome=attempt.outcome,
                    latency_ms=latency_ms,
                    error=attempt.error[:500],
                    raw_snippet=attempt.raw_snippet,
                    prompt_tokens=attempt.prompt_tokens,
                    completion_tokens=attempt.completion_tokens,
                    cost_usd=_estimate_cost(
                        model_name, attempt.prompt_tokens, attempt.completion_tokens
                    ),
                    memories_written=attempt.memories_written,
                    duplicates_skipped=attempt.duplicates_skipped,
                )
            )
    except Exception:
        logger.exception("记录抽取结果失败（不影响抽取本身）")


async def extract_and_store(user_id: str, session_id: str, user_msg: str, assistant_msg: str) -> None:
    attempt = _Attempt()
    started = time.perf_counter()
    model_name = settings.extractor_model

    try:
        data = await _call_extractor(user_msg, assistant_msg, attempt)
        if data is not None:
            await _store(user_id, session_id, data, attempt)
    except Exception as exc:
        attempt.outcome = OUTCOME_CALL_FAILED
        attempt.error = f"{type(exc).__name__}: {exc}"
        logger.warning("记忆抽取调用失败: %s", exc)
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000)
        if attempt.outcome == OUTCOME_OK:
            logger.info(
                "记忆抽取完成 latency_ms=%d written=%d duplicates=%d",
                latency_ms,
                attempt.memories_written,
                attempt.duplicates_skipped,
            )
        else:
            logger.warning(
                "记忆抽取未成功 outcome=%s latency_ms=%d error=%s",
                attempt.outcome,
                latency_ms,
                attempt.error,
            )
        await _record_attempt(user_id, session_id, attempt, latency_ms, model_name)

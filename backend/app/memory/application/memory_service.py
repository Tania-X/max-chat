import json
import logging
import re
import uuid

from app.memory.domain.models import Memory, UserProfile
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


async def extract_and_store(user_id: str, session_id: str, user_msg: str, assistant_msg: str) -> None:
    try:
        import litellm

        from app.agent_runtime.infrastructure.model_factory import operator_fallback_key

        extractor_model = (
            settings.extractor_model
            if "/" in settings.extractor_model
            else f"gemini/{settings.extractor_model}"
        )
        # 显式传 Key：不再依赖被其他请求改写过的进程级环境变量
        api_key = operator_fallback_key(extractor_model.split("/", 1)[0])
        call_kwargs = {"api_key": api_key} if api_key else {}
        resp = await litellm.acompletion(
            model=extractor_model,
            messages=[
                {"role": "user", "content": EXTRACT_PROMPT.format(user_msg=user_msg[:2000], assistant_msg=assistant_msg[:2000])}
            ],
            max_tokens=500,
            **call_kwargs,
        )
        text = resp.choices[0].message.content or ""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return
        data = json.loads(match.group())
    except Exception as exc:
        logger.warning("memory extraction failed: %s", exc)
        return

    async with async_session_factory() as db:
        repo = SqlAlchemyMemoryRepository(db)
        for item in data.get("memories", [])[:5]:
            content = (item.get("content") or "").strip()
            if not content:
                continue
            existing = await repo.search(user_id, [content[:20]], limit=1)
            if existing:
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
        profile_data = data.get("profile") or {}
        if profile_data:
            profile = await repo.get_profile(user_id)
            profile.data.update({k: v for k, v in profile_data.items() if v})
            await repo.save_profile(profile)

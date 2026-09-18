import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agent_runtime.application.model_config_service import ModelConfigService
from app.agent_runtime.application.runtime import AgentRuntime
from app.agent_runtime.infrastructure.model_config_repository import (
    SqlAlchemyModelConfigRepository,
)
from app.agent_runtime.infrastructure.model_factory import default_model_config
from app.conversation.application.session_service import SessionService
from app.conversation.domain.models import Message
from app.conversation.infrastructure.session_repository import SqlAlchemySessionRepository
from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.shared.config import get_settings
from app.shared.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


class ChatRequest(BaseModel):
    content: str


async def _gather_tools(user_id: str, db: AsyncSession) -> tuple[list, str]:
    try:
        from app.capability.application.tool_aggregator import gather_enabled_tools

        return await gather_enabled_tools(user_id, db)
    except ImportError:
        return [], ""


async def _memory_instruction(user_id: str, query: str, db: AsyncSession) -> str:
    try:
        from app.memory.application.memory_service import build_context_injection

        return await build_context_injection(user_id, query, db)
    except ImportError:
        return ""


def _schedule_memory_extraction(user_id: str, session_id: str, user_msg: str, assistant_msg: str):
    async def _run():
        try:
            from app.memory.application.memory_service import extract_and_store

            await extract_and_store(user_id, session_id, user_msg, assistant_msg)
        except ImportError:
            pass

    asyncio.create_task(_run())


@router.post("/{session_id}")
async def chat(
    session_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_repo = SqlAlchemySessionRepository(db)
    session_svc = SessionService(session_repo)
    chat_session = await session_svc.get_owned(user.id, session_id)

    model_svc = ModelConfigService(SqlAlchemyModelConfigRepository(db))
    model_config = await model_svc.resolve_for_chat(user.id, chat_session.model_config_id)
    if not model_config:
        model_config = default_model_config(user.id)

    history = await session_repo.list_messages(session_id, limit=settings.context_message_limit)
    tools, skill_instructions = await _gather_tools(user.id, db)
    instruction_extra = skill_instructions + await _memory_instruction(user.id, body.content, db)

    await session_repo.add_message(
        Message(id=str(uuid.uuid4()), session_id=session_id, user_id=user.id, role="user", content=body.content)
    )
    if len(history) == 0:
        chat_session.title = body.content[:30]
    await session_svc.touch(chat_session)

    runtime = AgentRuntime(tools=tools, instruction_extra=instruction_extra)
    user_id = user.id
    content = body.content

    async def event_stream():
        start = time.perf_counter()
        ttft_ms: int | None = None
        assistant_text = ""
        tool_events: list[dict] = []
        usage: dict = {}
        error_msg = ""
        async for ev in runtime.run(
            user_id=user_id,
            session_id=session_id,
            model_config=model_config,
            history=history,
            user_message=content,
        ):
            if ev["type"] == "text":
                if ttft_ms is None:
                    ttft_ms = round((time.perf_counter() - start) * 1000)
                yield {"event": "chunk", "data": json.dumps({"delta": ev["delta"]}, ensure_ascii=False)}
            elif ev["type"] in ("tool_call", "tool_result"):
                ev["ts_ms"] = round((time.perf_counter() - start) * 1000)
                tool_events.append(ev)
                yield {"event": ev["type"], "data": json.dumps(ev, ensure_ascii=False)}
            elif ev["type"] == "error":
                error_msg = ev["message"]
                yield {"event": "error", "data": json.dumps({"message": error_msg}, ensure_ascii=False)}
            elif ev["type"] == "done":
                assistant_text = ev["content"]
                usage = ev.get("usage") or {}

        duration_ms = round((time.perf_counter() - start) * 1000)
        message_id = str(uuid.uuid4())
        trace_id: str | None = None
        if assistant_text or tool_events:
            await session_repo.add_message(
                Message(
                    id=message_id,
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content=assistant_text,
                    tool_events=tool_events,
                )
            )
            if assistant_text:
                _schedule_memory_extraction(user_id, session_id, content, assistant_text)
        try:
            from app.observability.application.tracer import record_trace

            trace_id = await record_trace(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                model_config=model_config,
                tool_events=tool_events,
                usage=usage,
                ttft_ms=ttft_ms,
                duration_ms=duration_ms,
                error=error_msg,
            )
        except ImportError:
            pass
        completion_tokens = usage.get("completion_tokens", 0)
        stats = {
            "message_id": message_id,
            "trace_id": trace_id,
            "ttft_ms": ttft_ms,
            "duration_ms": duration_ms,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": completion_tokens,
            "tokens_per_second": round(completion_tokens / (duration_ms / 1000), 1) if duration_ms else 0,
        }
        yield {"event": "done", "data": json.dumps(stats, ensure_ascii=False)}

    return EventSourceResponse(event_stream())

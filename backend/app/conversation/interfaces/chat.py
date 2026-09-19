import asyncio
import json
import logging
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
from app.shared.database import async_session_factory, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()

# asyncio 对任务只持弱引用，不保存强引用时任务可能在执行完前被 GC 回收
_background_tasks: set[asyncio.Task] = set()


def _spawn_background(coro) -> None:
    """脱离请求生命周期执行协程，保留强引用并记录未捕获异常。"""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.warning("后台任务异常: %r", t.exception())

    task.add_done_callback(_on_done)


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
        except Exception:
            logger.exception("记忆抽取失败（不影响本轮回复）")

    _spawn_background(_run())


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
    content_in = body.content

    async def event_stream():
        start = time.perf_counter()
        ttft_ms: int | None = None
        assistant_text = ""
        tool_events: list[dict] = []
        usage: dict = {}
        error_msg = ""
        persisted = False
        completed = False

        async def persist_turn() -> dict:
            """落库本轮助手消息与 Trace。

            使用独立会话，不依赖请求作用域：客户端中途断开（用户点"停止生成"、
            关页面、网络中断）时请求会被取消，本函数仍会在后台完成写入，
            避免"用户消息已入库、回复却凭空消失"。
            """
            nonlocal persisted
            if persisted:
                return {}
            persisted = True

            duration_ms = round((time.perf_counter() - start) * 1000)
            message_id = str(uuid.uuid4())
            # 出错时也写入历史，保证刷新后看到的内容与当时界面一致
            content = assistant_text or (f"⚠️ 出错：{error_msg}" if error_msg else "")
            trace_id: str | None = None

            async with async_session_factory() as db:
                repo = SqlAlchemySessionRepository(db)
                if content or tool_events:
                    await repo.add_message(
                        Message(
                            id=message_id,
                            session_id=session_id,
                            user_id=user_id,
                            role="assistant",
                            content=content,
                            tool_events=tool_events,
                        )
                    )
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
                if trace_id and (content or tool_events):
                    await repo.set_message_trace_id(message_id, trace_id)

            if assistant_text and completed:
                # 仅对完整回复做记忆抽取，半截回复不值得沉淀为长期记忆
                _schedule_memory_extraction(user_id, session_id, content_in, assistant_text)

            completion_tokens = usage.get("completion_tokens", 0)
            return {
                "message_id": message_id,
                "trace_id": trace_id,
                "ttft_ms": ttft_ms,
                "duration_ms": duration_ms,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": completion_tokens,
                "tokens_per_second": round(completion_tokens / (duration_ms / 1000), 1)
                if duration_ms
                else 0,
            }

        try:
            async for ev in runtime.run(
                user_id=user_id,
                session_id=session_id,
                model_config=model_config,
                history=history,
                user_message=content_in,
            ):
                if ev["type"] == "text":
                    if ttft_ms is None:
                        ttft_ms = round((time.perf_counter() - start) * 1000)
                    # 边流边累积：客户端中途断开时也能保住已生成的部分
                    assistant_text += ev["delta"]
                    yield {"event": "chunk", "data": json.dumps({"delta": ev["delta"]}, ensure_ascii=False)}
                elif ev["type"] in ("tool_call", "tool_result"):
                    ev["ts_ms"] = round((time.perf_counter() - start) * 1000)
                    tool_events.append(ev)
                    yield {"event": ev["type"], "data": json.dumps(ev, ensure_ascii=False)}
                elif ev["type"] == "error":
                    error_msg = ev["message"]
                    yield {"event": "error", "data": json.dumps({"message": error_msg}, ensure_ascii=False)}
                elif ev["type"] == "done":
                    assistant_text = ev["content"] or assistant_text
                    usage = ev.get("usage") or {}
                    completed = True

            stats = await persist_turn()
            yield {"event": "done", "data": json.dumps(stats, ensure_ascii=False)}
        finally:
            # 正常路径已在上面落库；只有被取消/异常时才需要后台补齐
            if not persisted:
                _spawn_background(persist_turn())

    return EventSourceResponse(event_stream())

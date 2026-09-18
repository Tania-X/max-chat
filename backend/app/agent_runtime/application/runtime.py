from collections.abc import AsyncIterator

from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.infrastructure.model_factory import build_model
from app.conversation.domain.models import Message

APP_NAME = "adk_chat"

BASE_INSTRUCTION = (
    "你是一个乐于助人的 AI 助手，运行在类 ChatGPT 的网页应用中。"
    "使用中文回答（除非用户使用其他语言）。回答支持 Markdown 格式。"
    "如果可用工具能帮助回答，请主动调用工具。"
)


class AgentRuntime:
    """按用户/会话动态构建 ADK Agent 并运行，输出统一事件流。"""

    def __init__(self, tools: list | None = None, instruction_extra: str = ""):
        self.tools = tools or []
        self.instruction_extra = instruction_extra

    async def run(
        self,
        *,
        user_id: str,
        session_id: str,
        model_config: ModelConfig,
        history: list[Message],
        user_message: str,
    ) -> AsyncIterator[dict]:
        try:
            agent = LlmAgent(
                name="assistant",
                model=build_model(model_config),
                instruction=BASE_INSTRUCTION + self.instruction_extra,
                tools=self.tools,
            )
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                await session_service.append_event(
                    session=session,
                    event=Event(
                        author=role,
                        invocation_id="seed",
                        content=types.Content(role=role, parts=[types.Part(text=msg.content)]),
                    ),
                )
            runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)
            run_kwargs: dict = {}
            try:
                from google.adk.agents.run_config import RunConfig, StreamingMode

                run_kwargs["run_config"] = RunConfig(streaming_mode=StreamingMode.SSE)
            except Exception:
                pass

            accumulated = ""
            usage: dict = {}
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=user_message)]),
                **run_kwargs,
            ):
                um = getattr(event, "usage_metadata", None)
                if um:
                    usage = {
                        "prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
                        "completion_tokens": getattr(um, "candidates_token_count", 0) or 0,
                    }
                content = getattr(event, "content", None)
                if not content or not content.parts:
                    continue
                for part in content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc is not None:
                        yield {
                            "type": "tool_call",
                            "name": getattr(fc, "name", ""),
                            "args": dict(getattr(fc, "args", None) or {}),
                            "agent": getattr(event, "author", ""),
                        }
                    fr = getattr(part, "function_response", None)
                    if fr is not None:
                        yield {
                            "type": "tool_result",
                            "name": getattr(fr, "name", ""),
                            "response": getattr(fr, "response", None),
                        }
                    text = getattr(part, "text", None)
                    if text:
                        if getattr(event, "partial", False):
                            accumulated += text
                            yield {"type": "text", "delta": text}
                        elif not accumulated:
                            accumulated = text
                            yield {"type": "text", "delta": text}
            yield {"type": "done", "content": accumulated, "usage": usage}
        except Exception as exc:  # 模型不可达 / 配置错误等
            yield {"type": "error", "message": str(exc)}

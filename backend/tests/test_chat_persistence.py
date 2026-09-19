"""流式落库可靠性回归测试。

修复前的问题：
- assistant_text 只在 done 事件里赋值，客户端中途断开时它仍是空的
  → 已生成的部分回复不会入库，用户消息变成"永远没有回复"
- 落库写在生成器循环之后，请求被取消时整段代码不会执行
- 出错时不写历史，刷新后界面与历史不一致
- messages.trace_id 从不回填，刷新后 Trace 入口消失
"""

import asyncio
import json

from app.agent_runtime.application.runtime import AgentRuntime
from app.conversation.interfaces import chat as chat_module
from app.conversation.interfaces.chat import ChatRequest
from app.conversation.interfaces.chat import chat as chat_endpoint
from app.identity.infrastructure.user_repository import SqlAlchemyUserRepository


def _delta_of(chunk: dict) -> str:
    """SSE 事件 -> 文本增量。"""
    return json.loads(chunk["data"])["delta"]


async def _setup(client, register_user, auth):
    """注册用户 + 建会话，返回 (user_entity, session_id, token)。"""
    account = await register_user()
    token = account["token"]
    resp = await client.post("/api/sessions", json={"title": "t"}, headers=auth(token))
    assert resp.status_code == 200, resp.text
    return account["user"]["id"], resp.json()["id"], token


async def _drain_background():
    """等待 chat 模块派生的后台落库任务完成。"""
    tasks = [t for t in getattr(chat_module, "_background_tasks", set()) if not t.done()]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _messages(client, auth, token, session_id) -> list[dict]:
    resp = await client.get(f"/api/sessions/{session_id}/messages", headers=auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _patch_runtime(monkeypatch, events, exc: BaseException | None = None):
    """用假的 AgentRuntime.run 替换真实模型调用。"""

    async def fake_run(self, **kwargs):
        for ev in events:
            yield ev
        if exc is not None:
            raise exc

    monkeypatch.setattr(AgentRuntime, "run", fake_run)


async def _drive_chat(db_session, user_id, session_id, content="你好"):
    """直接驱动端点，返回 (响应对象, 用户实体)。"""
    user = await SqlAlchemyUserRepository(db_session).get_by_id(user_id)
    assert user is not None
    resp = await chat_endpoint(
        session_id=session_id, body=ChatRequest(content=content), user=user, db=db_session
    )
    return resp


async def test_partial_reply_persisted_when_client_disconnects(
    client, db_session, register_user, auth, monkeypatch
):
    """客户端中途断开（用户点"停止生成"）时，已生成的部分回复必须入库。

    断言口径：入库内容应等于断开前已经发给客户端的内容。
    """
    user_id, session_id, token = await _setup(client, register_user, auth)
    _patch_runtime(
        monkeypatch,
        [
            {"type": "text", "delta": "前半段"},
            {"type": "text", "delta": "后半段"},
        ],
    )

    resp = await _drive_chat(db_session, user_id, session_id)
    iterator = resp.body_iterator
    delivered = _delta_of(await iterator.__anext__())  # 第一个 chunk 已送达客户端
    await iterator.aclose()  # 模拟客户端断开
    await _drain_background()

    roles = [(m["role"], m["content"]) for m in await _messages(client, auth, token, session_id)]
    assert ("user", "你好") in roles
    assert ("assistant", delivered) in roles, f"已送达的部分回复未入库: {roles}"


async def test_partial_reply_accumulates_every_delivered_chunk(
    client, db_session, register_user, auth, monkeypatch
):
    """断开前送达多个 chunk 时，入库内容必须是全部拼接，而不是最后一段或空。"""
    user_id, session_id, token = await _setup(client, register_user, auth)
    _patch_runtime(
        monkeypatch,
        [
            {"type": "text", "delta": "前半段"},
            {"type": "text", "delta": "后半段"},
        ],
    )

    resp = await _drive_chat(db_session, user_id, session_id)
    iterator = resp.body_iterator
    delivered = _delta_of(await iterator.__anext__()) + _delta_of(await iterator.__anext__())
    await iterator.aclose()
    await _drain_background()

    assert delivered == "前半段后半段"
    roles = [(m["role"], m["content"]) for m in await _messages(client, auth, token, session_id)]
    assert ("assistant", "前半段后半段") in roles, f"多段回复未完整累积: {roles}"


async def test_error_reply_persisted_so_history_matches_ui(
    client, db_session, register_user, auth, monkeypatch
):
    """模型报错时也要写历史，避免刷新后"用户消息没有回复"。"""
    user_id, session_id, token = await _setup(client, register_user, auth)
    _patch_runtime(monkeypatch, [{"type": "error", "message": "模型不可达"}])

    resp = await _drive_chat(db_session, user_id, session_id)
    iterator = resp.body_iterator
    while True:
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            break
    await _drain_background()

    messages = await _messages(client, auth, token, session_id)
    assistants = [m for m in messages if m["role"] == "assistant"]
    assert len(assistants) == 1
    assert "模型不可达" in assistants[0]["content"]


async def test_completed_turn_backfills_trace_id(
    client, db_session, register_user, auth, monkeypatch
):
    """正常完成的回复要把 trace 回填到消息上，刷新后仍能查看 Trace。"""
    user_id, session_id, token = await _setup(client, register_user, auth)
    _patch_runtime(
        monkeypatch,
        [
            {"type": "text", "delta": "完整回复"},
            {
                "type": "done",
                "content": "完整回复",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        ],
    )

    resp = await _drive_chat(db_session, user_id, session_id)
    iterator = resp.body_iterator
    while True:
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            break
    await _drain_background()

    assistants = [m for m in await _messages(client, auth, token, session_id) if m["role"] == "assistant"]
    assert len(assistants) == 1
    assert assistants[0]["content"] == "完整回复"
    assert assistants[0]["trace_id"], "trace_id 未回填，刷新后 Trace 入口会消失"


async def test_completed_turn_persisted_once(
    client, db_session, register_user, auth, monkeypatch
):
    """正常路径下不应因为 finally 兜底而重复落库。"""
    user_id, session_id, token = await _setup(client, register_user, auth)
    _patch_runtime(
        monkeypatch,
        [
            {"type": "text", "delta": "唯一回复"},
            {"type": "done", "content": "唯一回复", "usage": {}},
        ],
    )

    resp = await _drive_chat(db_session, user_id, session_id)
    iterator = resp.body_iterator
    while True:
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            break
    await _drain_background()

    assistants = [m for m in await _messages(client, auth, token, session_id) if m["role"] == "assistant"]
    assert len(assistants) == 1, f"助手消息重复落库: {assistants}"

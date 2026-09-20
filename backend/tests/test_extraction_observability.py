"""记忆抽取可观测性回归测试。

修复前：抽取在后台异步执行，失败路径完全不可观测——
- 模型没吐 JSON 时直接 `return`，连日志都没有
- 未配置 Key 时会白跑一次请求，最终只留一条笼统的 warning
- 没有任何成功率、失败原因或开销的统计

这些用例在引入 extraction_runs 之前会失败（拿不到任何记录）。
"""

import json
import uuid
from types import SimpleNamespace

import litellm
import pytest

from app.agent_runtime.infrastructure import model_factory
from app.memory.application import memory_service
from app.memory.domain.models import Memory
from app.memory.infrastructure.memory_repository import SqlAlchemyMemoryRepository


def _response(content: str, prompt_tokens: int = 12, completion_tokens: int = 34):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def _json_response(payload: dict):
    return _response(json.dumps(payload, ensure_ascii=False))


@pytest.fixture
def with_key(monkeypatch):
    """让 operator_fallback_key 能取到一个假 Key。"""
    monkeypatch.setattr(
        model_factory,
        "settings",
        SimpleNamespace(google_api_key="test-extractor-key", openai_api_key=""),
    )


@pytest.fixture
def without_key(monkeypatch):
    monkeypatch.setattr(
        model_factory, "settings", SimpleNamespace(google_api_key="", openai_api_key="")
    )


@pytest.fixture
def patched_completion(monkeypatch):
    """替换 litellm.acompletion，并记录调用次数。"""

    def _install(handler):
        calls = {"n": 0}

        async def wrapper(**kwargs):
            calls["n"] += 1
            return await handler(**kwargs)

        monkeypatch.setattr(litellm, "acompletion", wrapper)
        return calls

    return _install


async def _stats(client, auth, token, days: int = 30) -> dict:
    resp = await client.get(f"/api/memory/extraction/stats?days={days}", headers=auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_missing_key_is_recorded_and_no_request_is_made(
    client, register_user, auth, without_key, patched_completion
):
    """未配置 Key 属于配置问题，应单独归类，而不是白跑一次请求后报笼统错误。"""
    account = await register_user()
    calls = patched_completion(lambda **_: None)

    await memory_service.extract_and_store(
        account["user"]["id"], str(uuid.uuid4()), "你好", "你好，有什么可以帮你？"
    )

    assert calls["n"] == 0, "没有 Key 时不应发起模型调用"
    stats = await _stats(client, auth, account["token"])
    assert stats["total"] == 1
    assert stats["failed"] == 1
    assert stats["by_outcome"].get("skipped_no_key") == 1
    assert "API Key" in stats["recent_failures"][0]["error"]


async def test_non_json_output_is_recorded_with_snippet(
    client, register_user, auth, with_key, patched_completion
):
    """模型返回散文而非 JSON —— 修复前这条路径是完全静默的。"""
    account = await register_user()
    patched_completion(lambda **_: _async_value(_response("抱歉，我无法完成这个请求。")))

    await memory_service.extract_and_store(
        account["user"]["id"], str(uuid.uuid4()), "你好", "抱歉，我无法完成这个请求。"
    )

    stats = await _stats(client, auth, account["token"])
    assert stats["by_outcome"].get("no_json") == 1
    failure = stats["recent_failures"][0]
    assert failure["outcome"] == "no_json"
    assert "无法完成" in failure["raw_snippet"], "应保留模型原始输出片段以便排查"


async def test_call_failure_is_recorded(
    client, register_user, auth, with_key, patched_completion
):
    account = await register_user()

    async def boom(**_):
        raise RuntimeError("429 rate limited")

    patched_completion(boom)

    await memory_service.extract_and_store(
        account["user"]["id"], str(uuid.uuid4()), "你好", "你好"
    )

    stats = await _stats(client, auth, account["token"])
    assert stats["by_outcome"].get("call_failed") == 1
    assert "rate limited" in stats["recent_failures"][0]["error"]


async def test_bad_schema_is_distinguished_from_no_json(
    client, register_user, auth, with_key, patched_completion
):
    """JSON 能解析但结构不对，应与"没有 JSON"分开统计。"""
    account = await register_user()
    patched_completion(lambda **_: _async_value(_json_response({"memories": "不是数组"})))

    await memory_service.extract_and_store(
        account["user"]["id"], str(uuid.uuid4()), "你好", "你好"
    )

    stats = await _stats(client, auth, account["token"])
    assert stats["by_outcome"].get("bad_schema") == 1
    assert "memories" in stats["recent_failures"][0]["error"]


async def test_success_records_counts_latency_and_cost(
    client, register_user, auth, with_key, patched_completion
):
    account = await register_user()
    payload = {
        "memories": [{"content": "用户是后端工程师", "category": "fact"}],
        "profile": {"职业": "后端工程师"},
    }
    patched_completion(lambda **_: _async_value(_json_response(payload)))

    await memory_service.extract_and_store(
        account["user"]["id"], str(uuid.uuid4()), "我是后端工程师", "了解"
    )

    stats = await _stats(client, auth, account["token"])
    assert stats["total"] == 1
    assert stats["ok"] == 1
    assert stats["failed"] == 0
    assert stats["failure_rate"] == 0
    assert stats["memories_written"] == 1
    assert stats["avg_latency_ms"] >= 0
    assert stats["recent_failures"] == []
    # 抽取开销此前完全不计入统计，现在应被折算（gemini-2.0-flash 在定价表内）
    assert stats["total_cost_usd"] > 0


async def test_duplicate_memory_is_counted_not_rewritten(
    client, db_session, register_user, auth, with_key, patched_completion
):
    account = await register_user()
    user_id = account["user"]["id"]
    await SqlAlchemyMemoryRepository(db_session).save(
        Memory(id=str(uuid.uuid4()), user_id=user_id, content="用户是后端工程师")
    )
    payload = {"memories": [{"content": "用户是后端工程师", "category": "fact"}]}
    patched_completion(lambda **_: _async_value(_json_response(payload)))

    await memory_service.extract_and_store(user_id, str(uuid.uuid4()), "我是后端工程师", "了解")

    stats = await _stats(client, auth, account["token"])
    assert stats["memories_written"] == 0
    assert stats["duplicates_skipped"] == 1


async def test_failure_rate_reflects_mixed_outcomes(
    client, register_user, auth, with_key, patched_completion
):
    account = await register_user()
    user_id = account["user"]["id"]
    session_id = str(uuid.uuid4())

    patched_completion(lambda **_: _async_value(_json_response({"memories": [], "profile": {}})))
    await memory_service.extract_and_store(user_id, session_id, "a", "b")

    async def boom(**_):
        raise RuntimeError("network down")

    patched_completion(boom)
    await memory_service.extract_and_store(user_id, session_id, "a", "b")

    stats = await _stats(client, auth, account["token"])
    assert stats["total"] == 2
    assert stats["ok"] == 1
    assert stats["failed"] == 1
    assert stats["failure_rate"] == 0.5


async def test_stats_are_scoped_to_the_current_user(client, register_user, auth, with_key, patched_completion):
    """抽取出错信息可能包含提示词片段，不能跨用户可见。"""
    owner = await register_user()
    other = await register_user()
    patched_completion(lambda **_: _async_value(_response("不是 JSON")))

    await memory_service.extract_and_store(
        owner["user"]["id"], str(uuid.uuid4()), "秘密内容", "不是 JSON"
    )

    assert (await _stats(client, auth, other["token"]))["total"] == 0
    assert (await _stats(client, auth, owner["token"]))["total"] == 1


async def test_stats_requires_authentication(client):
    resp = await client.get("/api/memory/extraction/stats")
    assert resp.status_code == 401


async def _async_value(value):
    return value

"""记忆归属校验回归测试（对应加固项 S4）。

修复前 DELETE /api/memory/{id} 只校验"已登录"，任何用户都能删除他人记忆。
"""

import uuid

from app.memory.domain.models import Memory
from app.memory.infrastructure.memory_repository import SqlAlchemyMemoryRepository


async def _seed_memory(db_session, user_id: str, content: str = "用户的私密偏好") -> str:
    memory_id = str(uuid.uuid4())
    await SqlAlchemyMemoryRepository(db_session).save(
        Memory(id=memory_id, user_id=user_id, content=content)
    )
    return memory_id


async def _list_memory_ids(client, auth, token: str) -> set[str]:
    resp = await client.get("/api/memory", headers=auth(token))
    assert resp.status_code == 200, resp.text
    return {m["id"] for m in resp.json()}


async def test_cannot_delete_other_users_memory(client, db_session, register_user, auth):
    victim = await register_user()
    attacker = await register_user()
    memory_id = await _seed_memory(db_session, victim["user"]["id"])

    resp = await client.delete(f"/api/memory/{memory_id}", headers=auth(attacker["token"]))

    # 统一 404：既不删成功，也不泄露该记忆是否存在
    assert resp.status_code == 404
    assert memory_id in await _list_memory_ids(client, auth, victim["token"])


async def test_owner_can_delete_own_memory(client, db_session, register_user, auth):
    owner = await register_user()
    memory_id = await _seed_memory(db_session, owner["user"]["id"])

    resp = await client.delete(f"/api/memory/{memory_id}", headers=auth(owner["token"]))

    assert resp.status_code == 200
    assert memory_id not in await _list_memory_ids(client, auth, owner["token"])


async def test_delete_requires_authentication(client):
    resp = await client.delete("/api/memory/does-not-matter")
    assert resp.status_code == 401


async def test_delete_unknown_memory_returns_404(client, register_user, auth):
    user = await register_user()
    resp = await client.delete(f"/api/memory/{uuid.uuid4()}", headers=auth(user["token"]))
    assert resp.status_code == 404

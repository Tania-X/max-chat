"""测试夹具。

关键点：必须在导入 app 之前设置环境变量——多个模块在 import 期就调用
get_settings()（例如 security.py 的模块级 settings）。同时把数据库与密钥
全部指向临时目录，测试绝不触碰真实 data/。
"""

import os
import tempfile
import uuid
from pathlib import Path

import pytest

TMP_ROOT = Path(tempfile.mkdtemp(prefix="max-chat-tests-"))

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TMP_ROOT / 'app.db'}"
os.environ["JWT_SECRET"] = "test-jwt-secret-not-for-production"
os.environ["CORS_ORIGINS"] = '["http://localhost:5173"]'
os.environ.pop("ALLOW_STDIO_MCP", None)


@pytest.fixture(scope="session")
def tmp_root() -> Path:
    return TMP_ROOT


@pytest.fixture
async def client():
    import httpx

    from app.main import app
    from app.shared.database import init_db

    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_session():
    from app.shared.database import async_session_factory, init_db

    await init_db()
    async with async_session_factory() as session:
        yield session


@pytest.fixture
def register_user(client):
    """注册一个新用户，返回 {token, user}。用户名随机，避免测试间互相干扰。"""

    async def _register(password: str = "pw-123456") -> dict:
        username = f"user_{uuid.uuid4().hex[:12]}"
        resp = await client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _register


@pytest.fixture
def auth():
    """构造 Authorization 头。"""

    def _headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _headers

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import get_settings

settings = get_settings()

IS_SQLITE = settings.database_url.startswith("sqlite")

if IS_SQLITE:
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # 并发写入（流式聊天 + 记忆抽取后台任务）时不要立刻抛 database is locked
    connect_args={"timeout": 30} if IS_SQLITE else {},
)


if IS_SQLITE:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
        """SQLite 默认的 rollback journal 在读写并发下极易锁库，改开 WAL。"""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    # 触发各 BC 的 ORM 模型注册
    import app.agent_runtime.infrastructure.models  # noqa: F401
    import app.capability.infrastructure.models  # noqa: F401
    import app.conversation.infrastructure.models  # noqa: F401
    import app.identity.infrastructure.models  # noqa: F401
    import app.memory.infrastructure.models  # noqa: F401
    import app.observability.infrastructure.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

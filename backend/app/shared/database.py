from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False)
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

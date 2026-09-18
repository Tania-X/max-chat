import json
from datetime import datetime

from sqlalchemy import delete, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.domain.models import Memory, UserProfile
from app.memory.domain.repository import MemoryRepository
from app.memory.infrastructure.models import MemoryORM, UserProfileORM


def _to_entity(orm: MemoryORM) -> Memory:
    return Memory(
        id=orm.id,
        user_id=orm.user_id,
        content=orm.content,
        category=orm.category,
        source_session_id=orm.source_session_id,
        created_at=orm.created_at,
    )


class SqlAlchemyMemoryRepository(MemoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: str, limit: int = 200) -> list[Memory]:
        stmt = (
            select(MemoryORM)
            .where(MemoryORM.user_id == user_id)
            .order_by(desc(MemoryORM.created_at))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def search(self, user_id: str, keywords: list[str], limit: int = 10) -> list[Memory]:
        stmt = select(MemoryORM).where(MemoryORM.user_id == user_id)
        if keywords:
            stmt = stmt.where(or_(*[MemoryORM.content.like(f"%{kw}%") for kw in keywords]))
        stmt = stmt.order_by(desc(MemoryORM.created_at)).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def save(self, memory: Memory) -> Memory:
        self.session.add(
            MemoryORM(
                id=memory.id,
                user_id=memory.user_id,
                content=memory.content,
                category=memory.category,
                source_session_id=memory.source_session_id,
                created_at=memory.created_at,
            )
        )
        await self.session.commit()
        return memory

    async def delete(self, memory_id: str) -> None:
        await self.session.execute(delete(MemoryORM).where(MemoryORM.id == memory_id))
        await self.session.commit()

    async def get_profile(self, user_id: str) -> UserProfile:
        orm = await self.session.get(UserProfileORM, user_id)
        if not orm:
            return UserProfile(user_id=user_id)
        return UserProfile(user_id=user_id, data=json.loads(orm.data or "{}"), updated_at=orm.updated_at)

    async def save_profile(self, profile: UserProfile) -> UserProfile:
        orm = await self.session.get(UserProfileORM, profile.user_id)
        payload = json.dumps(profile.data, ensure_ascii=False)
        if orm:
            orm.data = payload
            orm.updated_at = datetime.utcnow()
        else:
            self.session.add(UserProfileORM(user_id=profile.user_id, data=payload))
        await self.session.commit()
        return profile

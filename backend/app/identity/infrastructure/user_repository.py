from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.models import User
from app.identity.domain.repository import UserRepository
from app.identity.infrastructure.models import UserORM


def _to_entity(orm: UserORM) -> User:
    return User(
        id=orm.id,
        username=orm.username,
        password_hash=orm.password_hash,
        display_name=orm.display_name,
        created_at=orm.created_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        orm = await self.session.get(UserORM, user_id)
        return _to_entity(orm) if orm else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserORM).where(UserORM.username == username)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    async def save(self, user: User) -> User:
        orm = UserORM(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            display_name=user.display_name,
            created_at=user.created_at,
        )
        self.session.add(orm)
        await self.session.commit()
        return user

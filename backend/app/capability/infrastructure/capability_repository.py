import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capability.domain.models import Capability
from app.capability.domain.repository import CapabilityRepository
from app.capability.infrastructure.models import CapabilityORM


def _to_entity(orm: CapabilityORM) -> Capability:
    return Capability(
        id=orm.id,
        user_id=orm.user_id,
        type=orm.type,
        name=orm.name,
        description=orm.description,
        enabled=orm.enabled,
        config=json.loads(orm.config or "{}"),
        created_at=orm.created_at,
    )


class SqlAlchemyCapabilityRepository(CapabilityRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: str) -> list[Capability]:
        stmt = select(CapabilityORM).where(CapabilityORM.user_id == user_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def get(self, capability_id: str) -> Capability | None:
        orm = await self.session.get(CapabilityORM, capability_id)
        return _to_entity(orm) if orm else None

    async def find_by_name(self, user_id: str, type_: str, name: str) -> Capability | None:
        stmt = select(CapabilityORM).where(
            CapabilityORM.user_id == user_id,
            CapabilityORM.type == type_,
            CapabilityORM.name == name,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    async def save(self, capability: Capability) -> Capability:
        orm = await self.session.get(CapabilityORM, capability.id)
        if orm:
            orm.description = capability.description
            orm.enabled = capability.enabled
            orm.config = json.dumps(capability.config, ensure_ascii=False)
        else:
            self.session.add(
                CapabilityORM(
                    id=capability.id,
                    user_id=capability.user_id,
                    type=capability.type,
                    name=capability.name,
                    description=capability.description,
                    enabled=capability.enabled,
                    config=json.dumps(capability.config, ensure_ascii=False),
                    created_at=capability.created_at,
                )
            )
        await self.session.commit()
        return capability

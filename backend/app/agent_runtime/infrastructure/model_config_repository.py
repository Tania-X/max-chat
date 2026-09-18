from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.domain.repository import ModelConfigRepository
from app.agent_runtime.infrastructure.models import ModelConfigORM
from app.shared.security import decrypt_secret, encrypt_secret


def _to_entity(orm: ModelConfigORM) -> ModelConfig:
    return ModelConfig(
        id=orm.id,
        user_id=orm.user_id,
        provider=orm.provider,
        model_name=orm.model_name,
        api_key=decrypt_secret(orm.api_key_enc),
        base_url=orm.base_url,
        label=orm.label,
        is_default=orm.is_default,
        created_at=orm.created_at,
    )


class SqlAlchemyModelConfigRepository(ModelConfigRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: str) -> list[ModelConfig]:
        stmt = select(ModelConfigORM).where(ModelConfigORM.user_id == user_id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def get(self, config_id: str) -> ModelConfig | None:
        orm = await self.session.get(ModelConfigORM, config_id)
        return _to_entity(orm) if orm else None

    async def get_default(self, user_id: str) -> ModelConfig | None:
        stmt = select(ModelConfigORM).where(
            ModelConfigORM.user_id == user_id, ModelConfigORM.is_default.is_(True)
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        if not orm:
            stmt = select(ModelConfigORM).where(ModelConfigORM.user_id == user_id).limit(1)
            orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    async def save(self, config: ModelConfig) -> ModelConfig:
        if config.is_default:
            await self.session.execute(
                update(ModelConfigORM)
                .where(ModelConfigORM.user_id == config.user_id)
                .values(is_default=False)
            )
        orm = await self.session.get(ModelConfigORM, config.id)
        if orm:
            orm.provider = config.provider
            orm.model_name = config.model_name
            orm.base_url = config.base_url
            orm.label = config.label
            orm.is_default = config.is_default
            if config.api_key:
                orm.api_key_enc = encrypt_secret(config.api_key)
        else:
            self.session.add(
                ModelConfigORM(
                    id=config.id,
                    user_id=config.user_id,
                    provider=config.provider,
                    model_name=config.model_name,
                    api_key_enc=encrypt_secret(config.api_key),
                    base_url=config.base_url,
                    label=config.label,
                    is_default=config.is_default,
                    created_at=config.created_at,
                )
            )
        await self.session.commit()
        return config

    async def delete(self, config_id: str) -> None:
        orm = await self.session.get(ModelConfigORM, config_id)
        if orm:
            await self.session.delete(orm)
            await self.session.commit()

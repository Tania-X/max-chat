from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.application.model_config_service import ModelConfigService
from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.infrastructure.model_config_repository import (
    SqlAlchemyModelConfigRepository,
)
from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.shared.database import get_db

router = APIRouter(prefix="/api/models", tags=["models"])


def _svc(db: AsyncSession) -> ModelConfigService:
    return ModelConfigService(SqlAlchemyModelConfigRepository(db))


def _to_dict(c: ModelConfig) -> dict:
    return {
        "id": c.id,
        "provider": c.provider,
        "model_name": c.model_name,
        "label": c.label,
        "base_url": c.base_url,
        "has_api_key": bool(c.api_key),
        "is_default": c.is_default,
    }


class ModelConfigRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str = ""
    base_url: str = ""
    label: str = ""
    is_default: bool = False


@router.get("")
async def list_models(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return [_to_dict(c) for c in await _svc(db).list(user.id)]


@router.post("")
async def create_model(
    body: ModelConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _svc(db).create(user.id, body.model_dump())
    return _to_dict(config)


@router.put("/{config_id}")
async def update_model(
    config_id: str,
    body: ModelConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _svc(db).update(user.id, config_id, body.model_dump())
    return _to_dict(config)


@router.delete("/{config_id}")
async def delete_model(
    config_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _svc(db).delete(user.id, config_id)
    return {"ok": True}


@router.post("/test")
async def test_model(
    body: ModelConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(db)
    if body.api_key:
        config = ModelConfig(
            id="test", user_id=user.id, provider=body.provider,
            model_name=body.model_name, api_key=body.api_key, base_url=body.base_url,
        )
    else:
        configs = await svc.list(user.id)
        config = next(
            (c for c in configs if c.provider == body.provider and c.model_name == body.model_name),
            None,
        )
        if not config:
            config = ModelConfig(
                id="test", user_id=user.id, provider=body.provider,
                model_name=body.model_name, base_url=body.base_url,
            )
    return await svc.test_connection(config)

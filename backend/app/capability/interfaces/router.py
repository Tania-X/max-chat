from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.capability.application.capability_service import CapabilityService
from app.capability.infrastructure.capability_repository import SqlAlchemyCapabilityRepository
from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.shared.database import get_db

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


def _svc(db: AsyncSession) -> CapabilityService:
    return CapabilityService(SqlAlchemyCapabilityRepository(db))


def _to_dict(c) -> dict:
    return {
        "id": c.id,
        "type": c.type,
        "name": c.name,
        "description": c.description,
        "enabled": c.enabled,
        "config": c.config,
    }


@router.get("")
async def list_capabilities(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return [_to_dict(c) for c in await _svc(db).sync_and_list(user.id)]


class EnabledRequest(BaseModel):
    enabled: bool


@router.put("/{capability_id}/enabled")
async def set_enabled(
    capability_id: str,
    body: EnabledRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _to_dict(await _svc(db).set_enabled(user.id, capability_id, body.enabled))


class ConfigRequest(BaseModel):
    config: dict


@router.put("/{capability_id}/config")
async def update_config(
    capability_id: str,
    body: ConfigRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _to_dict(await _svc(db).update_config(user.id, capability_id, body.config))


class McpServerRequest(BaseModel):
    name: str
    description: str = ""
    config: dict  # {transport: stdio|sse, command, args, env} 或 {transport: sse, url, headers}


@router.post("/mcp")
async def add_mcp_server(
    body: McpServerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _to_dict(await _svc(db).add_mcp_server(user.id, body.name, body.description, body.config))

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.application.session_service import SessionService
from app.conversation.infrastructure.session_repository import SqlAlchemySessionRepository
from app.conversation.interfaces.chat import router as chat_router
from app.identity.domain.models import User
from app.identity.interfaces.deps import get_current_user
from app.shared.database import get_db

router = APIRouter(tags=["conversation"])
sessions_router = APIRouter(prefix="/api/sessions")


def _svc(db: AsyncSession) -> SessionService:
    return SessionService(SqlAlchemySessionRepository(db))


class CreateSessionRequest(BaseModel):
    title: str = "新会话"


class RenameSessionRequest(BaseModel):
    title: str


class SetModelRequest(BaseModel):
    model_config_id: str | None = None


@sessions_router.get("")
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sessions = await _svc(db).list_sessions(user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "model_config_id": s.model_config_id,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@sessions_router.post("")
async def create_session(
    body: CreateSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _svc(db).create_session(user.id, body.title)
    return {"id": s.id, "title": s.title, "model_config_id": s.model_config_id}


@sessions_router.patch("/{session_id}")
async def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _svc(db).rename(user.id, session_id, body.title)
    return {"id": s.id, "title": s.title}


@sessions_router.put("/{session_id}/model")
async def set_session_model(
    session_id: str,
    body: SetModelRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _svc(db).set_model(user.id, session_id, body.model_config_id)
    return {"id": s.id, "model_config_id": s.model_config_id}


@sessions_router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _svc(db).delete(user.id, session_id)
    return {"ok": True}


@sessions_router.get("/{session_id}/messages")
async def list_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages = await _svc(db).history(user.id, session_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_events": m.tool_events,
            "trace_id": m.trace_id,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


router.include_router(sessions_router)
router.include_router(chat_router)

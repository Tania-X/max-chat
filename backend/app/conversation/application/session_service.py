import uuid
from datetime import datetime

from app.conversation.domain.models import ChatSession, Message
from app.conversation.domain.repository import SessionRepository
from app.shared.exceptions import ForbiddenError, NotFoundError


class SessionService:
    def __init__(self, repo: SessionRepository):
        self.repo = repo

    async def list_sessions(self, user_id: str) -> list[ChatSession]:
        return await self.repo.list_by_user(user_id)

    async def create_session(self, user_id: str, title: str = "新会话") -> ChatSession:
        session = ChatSession(id=str(uuid.uuid4()), user_id=user_id, title=title or "新会话")
        return await self.repo.save(session)

    async def get_owned(self, user_id: str, session_id: str) -> ChatSession:
        session = await self.repo.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        if session.user_id != user_id:
            raise ForbiddenError("无权访问该会话")
        return session

    async def rename(self, user_id: str, session_id: str, title: str) -> ChatSession:
        session = await self.get_owned(user_id, session_id)
        session.title = title.strip() or session.title
        session.updated_at = datetime.utcnow()
        return await self.repo.save(session)

    async def set_model(self, user_id: str, session_id: str, model_config_id: str | None) -> ChatSession:
        session = await self.get_owned(user_id, session_id)
        session.model_config_id = model_config_id
        session.updated_at = datetime.utcnow()
        return await self.repo.save(session)

    async def delete(self, user_id: str, session_id: str) -> None:
        await self.get_owned(user_id, session_id)
        await self.repo.delete(session_id)

    async def history(self, user_id: str, session_id: str) -> list[Message]:
        await self.get_owned(user_id, session_id)
        return await self.repo.list_messages(session_id)

    async def touch(self, session: ChatSession) -> None:
        session.updated_at = datetime.utcnow()
        await self.repo.save(session)

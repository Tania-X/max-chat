import json

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.domain.models import ChatSession, Message
from app.conversation.domain.repository import SessionRepository
from app.conversation.infrastructure.models import ChatSessionORM, MessageORM


def _session_to_entity(orm: ChatSessionORM) -> ChatSession:
    return ChatSession(
        id=orm.id,
        user_id=orm.user_id,
        title=orm.title,
        model_config_id=orm.model_config_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _message_to_entity(orm: MessageORM) -> Message:
    return Message(
        id=orm.id,
        session_id=orm.session_id,
        user_id=orm.user_id,
        role=orm.role,
        content=orm.content,
        tool_events=json.loads(orm.tool_events or "[]"),
        trace_id=orm.trace_id,
        created_at=orm.created_at,
    )


class SqlAlchemySessionRepository(SessionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: str) -> list[ChatSession]:
        stmt = (
            select(ChatSessionORM)
            .where(ChatSessionORM.user_id == user_id)
            .order_by(desc(ChatSessionORM.updated_at))
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_session_to_entity(r) for r in rows]

    async def get(self, session_id: str) -> ChatSession | None:
        orm = await self.session.get(ChatSessionORM, session_id)
        return _session_to_entity(orm) if orm else None

    async def save(self, chat_session: ChatSession) -> ChatSession:
        orm = await self.session.get(ChatSessionORM, chat_session.id)
        if orm:
            orm.title = chat_session.title
            orm.model_config_id = chat_session.model_config_id
            orm.updated_at = chat_session.updated_at
        else:
            orm = ChatSessionORM(
                id=chat_session.id,
                user_id=chat_session.user_id,
                title=chat_session.title,
                model_config_id=chat_session.model_config_id,
                created_at=chat_session.created_at,
                updated_at=chat_session.updated_at,
            )
            self.session.add(orm)
        await self.session.commit()
        return chat_session

    async def delete(self, session_id: str) -> None:
        await self.session.execute(delete(MessageORM).where(MessageORM.session_id == session_id))
        await self.session.execute(delete(ChatSessionORM).where(ChatSessionORM.id == session_id))
        await self.session.commit()

    async def add_message(self, message: Message) -> Message:
        self.session.add(
            MessageORM(
                id=message.id,
                session_id=message.session_id,
                user_id=message.user_id,
                role=message.role,
                content=message.content,
                tool_events=json.dumps(message.tool_events, ensure_ascii=False),
                trace_id=message.trace_id,
                created_at=message.created_at,
            )
        )
        await self.session.commit()
        return message

    async def list_messages(self, session_id: str, limit: int | None = None) -> list[Message]:
        stmt = select(MessageORM).where(MessageORM.session_id == session_id)
        if limit:
            stmt = stmt.order_by(desc(MessageORM.created_at)).limit(limit)
            rows = (await self.session.execute(stmt)).scalars().all()
            return [_message_to_entity(r) for r in reversed(rows)]
        stmt = stmt.order_by(MessageORM.created_at)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_message_to_entity(r) for r in rows]

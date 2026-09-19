from abc import ABC, abstractmethod

from app.conversation.domain.models import ChatSession, Message


class SessionRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[ChatSession]: ...

    @abstractmethod
    async def get(self, session_id: str) -> ChatSession | None: ...

    @abstractmethod
    async def save(self, session: ChatSession) -> ChatSession: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def add_message(self, message: Message) -> Message: ...

    @abstractmethod
    async def set_message_trace_id(self, message_id: str, trace_id: str) -> None:
        """回填助手消息关联的 trace，使刷新后仍能查看该条回复的 Trace。"""

    @abstractmethod
    async def list_messages(self, session_id: str, limit: int | None = None) -> list[Message]: ...

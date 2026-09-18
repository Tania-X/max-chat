from abc import ABC, abstractmethod

from app.identity.domain.models import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...

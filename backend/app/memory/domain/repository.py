from abc import ABC, abstractmethod

from app.memory.domain.models import Memory, UserProfile


class MemoryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str, limit: int = 200) -> list[Memory]: ...

    @abstractmethod
    async def search(self, user_id: str, keywords: list[str], limit: int = 10) -> list[Memory]: ...

    @abstractmethod
    async def save(self, memory: Memory) -> Memory: ...

    @abstractmethod
    async def delete(self, memory_id: str) -> None: ...

    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile: ...

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> UserProfile: ...

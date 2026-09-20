from abc import ABC, abstractmethod

from app.memory.domain.models import ExtractionRun, ExtractionStats, Memory, UserProfile


class MemoryRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str, limit: int = 200) -> list[Memory]: ...

    @abstractmethod
    async def search(self, user_id: str, keywords: list[str], limit: int = 10) -> list[Memory]: ...

    @abstractmethod
    async def get(self, memory_id: str) -> Memory | None: ...

    @abstractmethod
    async def save(self, memory: Memory) -> Memory: ...

    @abstractmethod
    async def delete(self, user_id: str, memory_id: str) -> None:
        """删除归属 user_id 的记忆。user_id 为强制约束，避免越权删除他人数据。"""

    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile: ...

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> UserProfile: ...


class ExtractionRunRepository(ABC):
    """记忆抽取尝试的记录与聚合，用于暴露成功率与失败原因。"""

    @abstractmethod
    async def save(self, run: ExtractionRun) -> ExtractionRun: ...

    @abstractmethod
    async def stats(self, user_id: str, days: int = 30) -> ExtractionStats: ...

    @abstractmethod
    async def recent_failures(self, user_id: str, limit: int = 5) -> list[ExtractionRun]: ...

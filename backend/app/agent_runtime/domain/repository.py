from abc import ABC, abstractmethod

from app.agent_runtime.domain.models import ModelConfig


class ModelConfigRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[ModelConfig]: ...

    @abstractmethod
    async def get(self, config_id: str) -> ModelConfig | None: ...

    @abstractmethod
    async def get_default(self, user_id: str) -> ModelConfig | None: ...

    @abstractmethod
    async def save(self, config: ModelConfig) -> ModelConfig: ...

    @abstractmethod
    async def delete(self, config_id: str) -> None: ...

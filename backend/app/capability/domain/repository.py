from abc import ABC, abstractmethod

from app.capability.domain.models import Capability


class CapabilityRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Capability]: ...

    @abstractmethod
    async def get(self, capability_id: str) -> Capability | None: ...

    @abstractmethod
    async def find_by_name(self, user_id: str, type_: str, name: str) -> Capability | None: ...

    @abstractmethod
    async def save(self, capability: Capability) -> Capability: ...

import uuid

from app.capability.domain.models import Capability
from app.capability.domain.repository import CapabilityRepository
from app.capability.infrastructure.plugin_manager import scan_plugins
from app.capability.infrastructure.skill_manager import scan_skills
from app.shared.exceptions import ForbiddenError, NotFoundError


class CapabilityService:
    def __init__(self, repo: CapabilityRepository):
        self.repo = repo

    async def sync_and_list(self, user_id: str) -> list[Capability]:
        """扫描文件系统能力，为新发现的能力注册用户级记录。"""
        existing = {(c.type, c.name): c for c in await self.repo.list_by_user(user_id)}
        for manifest in scan_plugins():
            if ("plugin", manifest["name"]) not in existing:
                cap = Capability(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    type="plugin",
                    name=manifest["name"],
                    description=manifest.get("description", ""),
                    enabled=manifest.get("enabled_default", True),
                )
                existing[("plugin", cap.name)] = await self.repo.save(cap)
        for skill in scan_skills():
            if ("skill", skill["name"]) not in existing:
                cap = Capability(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    type="skill",
                    name=skill["name"],
                    description=skill.get("description", ""),
                    enabled=skill.get("enabled_default", True),
                )
                existing[("skill", cap.name)] = await self.repo.save(cap)
        return sorted(existing.values(), key=lambda c: (c.type, c.name))

    async def set_enabled(self, user_id: str, capability_id: str, enabled: bool) -> Capability:
        cap = await self._get_owned(user_id, capability_id)
        cap.enabled = enabled
        return await self.repo.save(cap)

    async def update_config(self, user_id: str, capability_id: str, config: dict) -> Capability:
        cap = await self._get_owned(user_id, capability_id)
        cap.config = config
        return await self.repo.save(cap)

    async def add_mcp_server(self, user_id: str, name: str, description: str, config: dict) -> Capability:
        existing = await self.repo.find_by_name(user_id, "mcp", name)
        if existing:
            existing.config = config
            existing.description = description
            return await self.repo.save(existing)
        cap = Capability(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type="mcp",
            name=name,
            description=description,
            enabled=True,
            config=config,
        )
        return await self.repo.save(cap)

    async def _get_owned(self, user_id: str, capability_id: str) -> Capability:
        cap = await self.repo.get(capability_id)
        if not cap:
            raise NotFoundError("能力不存在")
        if cap.user_id != user_id:
            raise ForbiddenError("无权操作该能力")
        return cap

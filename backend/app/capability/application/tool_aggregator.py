import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.capability.infrastructure.capability_repository import SqlAlchemyCapabilityRepository
from app.capability.infrastructure.mcp_manager import load_mcp_tools
from app.capability.infrastructure.plugin_manager import load_plugin_tools, scan_plugins
from app.capability.infrastructure.skill_manager import (
    load_skill_tools,
    scan_skills,
    skill_instruction,
)

logger = logging.getLogger(__name__)


async def gather_enabled_tools(user_id: str, db: AsyncSession) -> tuple[list, str]:
    """聚合所有启用能力源的工具与 skill 指令，返回 (tools, skill_instructions)。"""
    repo = SqlAlchemyCapabilityRepository(db)
    capabilities = [c for c in await repo.list_by_user(user_id) if c.enabled]
    if not capabilities:
        return [], ""

    plugins = {m["name"]: m for m in scan_plugins()}
    skills = {s["name"]: s for s in scan_skills()}

    tools: list = []
    instructions: list[str] = []
    mcp_tasks: list[asyncio.Task] = []

    for cap in capabilities:
        if cap.type == "plugin" and cap.name in plugins:
            tools.extend(load_plugin_tools(plugins[cap.name], cap.config))
        elif cap.type == "skill" and cap.name in skills:
            skill = skills[cap.name]
            text = skill_instruction(skill, cap.config)
            if text:
                instructions.append(f"【技能：{cap.name}】\n{text}")
            tools.extend(load_skill_tools(skill, cap.config))
        elif cap.type == "mcp":
            mcp_tasks.append(asyncio.create_task(load_mcp_tools(cap.name, cap.config)))

    if mcp_tasks:
        for result in await asyncio.gather(*mcp_tasks):
            tools.extend(result)

    extra = ""
    if instructions:
        extra = "\n\n你已获得以下技能，请在合适的场景遵循其指引：\n" + "\n\n".join(instructions)
    return tools, extra

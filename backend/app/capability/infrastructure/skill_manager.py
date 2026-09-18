import json
import logging
from pathlib import Path

from app.capability.infrastructure.plugin_manager import load_plugin_tools
from app.shared.config import BASE_DIR

logger = logging.getLogger(__name__)

SKILLS_DIR = BASE_DIR / "skills"


def scan_skills() -> list[dict]:
    """扫描 skills/ 目录，每个 skill 为 skill.json（指令模板）+ 可选 entry.py（工具集）。"""
    skills: list[dict] = []
    if not SKILLS_DIR.exists():
        return skills
    for child in sorted(SKILLS_DIR.iterdir()):
        manifest_path = child / "skill.json"
        if not child.is_dir() or not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.setdefault("name", child.name)
            manifest["_dir"] = str(child)
            skills.append(manifest)
        except Exception as exc:
            logger.warning("invalid skill manifest %s: %s", manifest_path, exc)
    return skills


def load_skill_tools(skill: dict, config: dict) -> list:
    if not (Path(skill["_dir"]) / skill.get("entry", "entry.py")).exists():
        return []
    return load_plugin_tools(skill, config)


def skill_instruction(skill: dict, config: dict) -> str:
    template = skill.get("instruction", "")
    for key, value in config.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template

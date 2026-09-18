import importlib.util
import json
import logging
from pathlib import Path

from app.shared.config import BASE_DIR

logger = logging.getLogger(__name__)

PLUGINS_DIR = BASE_DIR / "plugins"


def scan_plugins() -> list[dict]:
    """扫描 plugins/ 目录，返回 manifest 列表。"""
    manifests: list[dict] = []
    if not PLUGINS_DIR.exists():
        return manifests
    for child in sorted(PLUGINS_DIR.iterdir()):
        manifest_path = child / "manifest.json"
        if not child.is_dir() or not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.setdefault("name", child.name)
            manifest["_dir"] = str(child)
            manifests.append(manifest)
        except Exception as exc:
            logger.warning("invalid plugin manifest %s: %s", manifest_path, exc)
    return manifests


def load_plugin_tools(manifest: dict, config: dict) -> list:
    """动态加载插件入口并包装为 ADK FunctionTool（按 mtime 热加载）。"""
    from google.adk.tools import FunctionTool

    plugin_dir = Path(manifest["_dir"])
    entry = plugin_dir / manifest.get("entry", "entry.py")
    if not entry.exists():
        logger.warning("plugin entry missing: %s", entry)
        return []
    mtime = int(entry.stat().st_mtime)
    module_name = f"plugin_{manifest['name']}_{mtime}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, entry)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw_tools = (
            module.get_tools(config)
            if hasattr(module, "get_tools")
            else getattr(module, "tools", [])
        )
        return [FunctionTool(func=fn) if callable(fn) else fn for fn in raw_tools]
    except Exception as exc:
        logger.warning("load plugin %s failed: %s", manifest["name"], exc)
        return []

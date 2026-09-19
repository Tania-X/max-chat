"""JWT 签名密钥与 Fernet 加密密钥的解析与持久化。

本地优先场景不应要求用户手工生成密钥，但更绝不能使用公开的默认值。
策略：环境变量优先；未配置（或仍是历史公开占位值）时首次启动自动生成，
并以 0600 权限持久化到数据目录下的 ``secrets.json``，保证重启后已签发的
token 与已加密的 API Key 依然可用。

``secrets.json`` 位于 ``data/`` 目录内，已被 .gitignore / .dockerignore 排除，
并与 SQLite 数据同处 Docker 命名卷，容器重建不会丢失。
"""

import json
import logging
import os
import secrets as _secrets
import stat
import threading
from collections.abc import Callable
from pathlib import Path

from cryptography.fernet import Fernet

from app.shared.config import BASE_DIR, get_settings

logger = logging.getLogger(__name__)

SECRETS_FILENAME = "secrets.json"

# 历史版本 .env.example 中使用过的公开占位值：一旦检测到即视同未配置，
# 否则任何知道该字符串的人都能伪造 JWT。
LEGACY_PLACEHOLDER_SECRETS = frozenset({"change-me-to-a-random-string"})

_lock = threading.Lock()
_cache: dict[str, str] | None = None


def data_dir() -> Path:
    """密钥与数据库共用的数据目录（保证随数据卷一起持久化）。"""
    url = get_settings().database_url
    if url.startswith("sqlite"):
        path = Path(url.split("///")[-1])
        if not path.is_absolute():
            path = BASE_DIR / path
        return path.parent
    return BASE_DIR / "data"


def secrets_path() -> Path:
    return data_dir() / SECRETS_FILENAME


def _load() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    path = secrets_path()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                _cache = {str(k): str(v) for k, v in loaded.items()}
                return _cache
        except (OSError, ValueError) as exc:
            logger.warning("读取 %s 失败（%s），将重新生成密钥", path, exc)
    _cache = {}
    return _cache


def _persist(values: dict[str, str]) -> None:
    path = secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{SECRETS_FILENAME}.tmp")
    tmp.write_text(json.dumps(values, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600，仅属主可读写
    os.replace(tmp, path)


def _get_or_create(name: str, factory: Callable[[], str]) -> str:
    """读取已有密钥，缺失时生成并持久化。进程内始终返回同一个值。"""
    with _lock:
        values = _load()
        existing = values.get(name)
        if existing:
            return existing
        value = factory()
        values[name] = value
        try:
            _persist(values)
            logger.info("已自动生成 %s 并保存到 %s", name, secrets_path())
        except OSError as exc:
            # 目录不可写时不阻断启动，但要明确告知密钥不会跨重启保留
            logger.warning(
                "无法写入 %s（%s）：%s 仅在本进程内有效，重启后已签发的 token 与已加密的 API Key 将失效",
                secrets_path(),
                exc,
                name,
            )
        return value


def get_jwt_secret() -> str:
    configured = (get_settings().jwt_secret or "").strip()
    if configured and configured not in LEGACY_PLACEHOLDER_SECRETS:
        return configured
    if configured:
        logger.warning(
            "检测到公开的默认 JWT_SECRET，已改用自动生成的密钥；"
            "此前签发的 token 全部失效，请重新登录"
        )
    return _get_or_create("jwt_secret", lambda: _secrets.token_urlsafe(48))


def get_fernet_key() -> str:
    configured = (get_settings().fernet_key or "").strip()
    if configured:
        return configured
    return _get_or_create("fernet_key", lambda: Fernet.generate_key().decode())


def ensure_secrets() -> None:
    """启动时预热，让密钥生成/回退的日志出现在启动阶段而非首个请求。"""
    get_jwt_secret()
    get_fernet_key()


def reset_cache() -> None:
    """仅供测试：清除进程内缓存，使 get_settings 变更后重新解析。"""
    global _cache
    with _lock:
        _cache = None

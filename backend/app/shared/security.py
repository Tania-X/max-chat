import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.shared.config import get_settings
from app.shared.secrets_store import get_fernet_key, get_jwt_secret

logger = logging.getLogger(__name__)

settings = get_settings()

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Fernet 实例（进程内缓存）。密钥由 secrets_store 保证始终可用。"""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_fernet_key().encode())
    return _fernet


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, get_jwt_secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        # algorithms 由 Settings 校验为 HMAC 白名单，杜绝 alg=none 等伪造路径
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def encrypt_secret(plain: str) -> str:
    """加密 API Key 后入库；不存在"无密钥则明文落库"的静默降级。"""
    if not plain:
        return plain
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str) -> str:
    """解密 API Key。

    兼容历史数据：早期版本在未配置 FERNET_KEY 时会明文入库，这类值（以及用
    旧密钥加密的值）无法解密，此时原样返回，避免既有配置直接不可用。
    """
    if not cipher:
        return cipher
    try:
        return _get_fernet().decrypt(cipher.encode()).decode()
    except (InvalidToken, ValueError):
        logger.warning("API Key 解密失败，按明文处理（历史明文数据或加密密钥已变更）")
        return cipher

from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.shared.config import get_settings

settings = get_settings()

_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is None and settings.fernet_key:
        _fernet = Fernet(settings.fernet_key.encode())
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
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def encrypt_secret(plain: str) -> str:
    f = _get_fernet()
    if not f or not plain:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str) -> str:
    f = _get_fernet()
    if not f or not cipher:
        return cipher
    try:
        return f.decrypt(cipher.encode()).decode()
    except Exception:
        return cipher

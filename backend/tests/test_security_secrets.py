"""密钥与 JWT 回归测试（对应加固项 S2 / S5）。

S2：默认 JWT 密钥曾是公开字符串，任何人都能伪造 token
S5：FERNET_KEY 为空时 API Key 会静默明文入库
"""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.shared import secrets_store
from app.shared.config import Settings
from app.shared.security import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
)

PLACEHOLDER = "change-me-to-a-random-string"


def _settings(tmp_root, **overrides) -> Settings:
    values = {"database_url": f"sqlite+aiosqlite:///{tmp_root / 'secrets-test.db'}"}
    values.update(overrides)
    return Settings(**values)


def _b64(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# ---------- S2：JWT ----------


def test_legacy_placeholder_secret_is_replaced(monkeypatch, tmp_root):
    """公开占位密钥被视同未配置，改用自动生成的强随机密钥并持久化。"""
    secrets_store.reset_cache()
    monkeypatch.setattr(
        secrets_store, "get_settings", lambda: _settings(tmp_root, jwt_secret=PLACEHOLDER)
    )
    secret = secrets_store.get_jwt_secret()

    assert secret != PLACEHOLDER
    assert len(secret) >= 32

    # 持久化后可复现（重启不会让已签发 token 失效）
    secrets_store.reset_cache()
    assert secrets_store.get_jwt_secret() == secret

    secrets_store.reset_cache()


@pytest.mark.parametrize("algorithm", ["none", "None", "RS256", "ES256", "HS255", ""])
def test_unsupported_jwt_algorithm_rejected(algorithm, tmp_root):
    """none / 非对称算法一律拒绝，避免签名校验被绕过。"""
    with pytest.raises(ValidationError):
        _settings(tmp_root, jwt_algorithm=algorithm)


@pytest.mark.parametrize("algorithm", ["HS256", "hs384", "HS512"])
def test_supported_jwt_algorithm_normalized(algorithm, tmp_root):
    assert _settings(tmp_root, jwt_algorithm=algorithm).jwt_algorithm == algorithm.upper()


def test_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_unsigned_alg_none_token_rejected():
    """手工构造的 alg=none 无签名 token 必须被拒绝。"""
    exp = int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp())
    forged = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': 'victim', 'exp': exp})}."
    assert decode_access_token(forged) is None


def test_token_signed_with_other_secret_rejected():
    """用其它密钥签发的 token 必须被拒绝（证明校验真的用了服务端密钥）。"""
    from jose import jwt as jose_jwt

    exp = datetime.now(timezone.utc) + timedelta(days=1)
    forged = jose_jwt.encode({"sub": "victim", "exp": exp}, "attacker-secret", algorithm="HS256")
    assert decode_access_token(forged) is None


# ---------- S5：API Key 加密 ----------


def test_api_key_is_encrypted_at_rest():
    plain = "sk-test-1234567890abcdef"
    cipher = encrypt_secret(plain)

    assert cipher != plain
    assert plain not in cipher
    assert decrypt_secret(cipher) == plain


def test_empty_api_key_stays_empty():
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_legacy_plaintext_value_still_readable():
    """历史明文数据（或密钥轮换后）不应导致配置直接不可用。"""
    assert decrypt_secret("sk-legacy-plaintext") == "sk-legacy-plaintext"


def test_fernet_key_is_persisted(monkeypatch, tmp_root):
    """未配置 FERNET_KEY 时自动生成并落盘，而不是退回明文存储。"""
    secrets_store.reset_cache()
    monkeypatch.setattr(secrets_store, "get_settings", lambda: _settings(tmp_root))

    key = secrets_store.get_fernet_key()
    assert key

    secrets_store.reset_cache()
    assert secrets_store.get_fernet_key() == key

    secrets_store.reset_cache()

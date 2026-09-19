"""模型 Key 隔离回归测试（对应加固项 S3）。

修复前存在两个问题：
1. 任意非 gemini provider 都会回退到运营者的 OPENAI_API_KEY
   → 把 OpenAI 的密钥发给 DeepSeek 等第三方端点；
2. 用户 Key 被写进进程级 os.environ 且从不清理
   → 并发/多用户场景下互相串用，甚至用他人的 Key 计费。
"""

import os
from types import SimpleNamespace

import pytest

from app.agent_runtime.domain.models import ModelConfig
from app.agent_runtime.infrastructure import model_factory
from app.shared.exceptions import DomainError


def _config(**overrides) -> ModelConfig:
    values = {"id": "c1", "user_id": "u1", "provider": "deepseek", "model_name": "deepseek-chat"}
    values.update(overrides)
    return ModelConfig(**values)


@pytest.fixture
def operator_keys(monkeypatch):
    monkeypatch.setattr(
        model_factory,
        "settings",
        SimpleNamespace(google_api_key="OPERATOR-GOOGLE", openai_api_key="OPERATOR-OPENAI"),
    )


def test_no_cross_provider_key_fallback(operator_keys):
    """deepseek 不得拿到 OpenAI 的密钥。"""
    assert model_factory.resolve_api_key(_config(provider="deepseek")) == ""
    assert model_factory.resolve_api_key(_config(provider="anthropic")) == ""


def test_operator_fallback_only_for_matching_provider(operator_keys):
    assert model_factory.resolve_api_key(_config(provider="openai")) == "OPERATOR-OPENAI"
    assert model_factory.resolve_api_key(_config(provider="gemini")) == "OPERATOR-GOOGLE"


def test_user_key_takes_precedence(operator_keys):
    config = _config(provider="openai", api_key="USER-KEY")
    assert model_factory.resolve_api_key(config) == "USER-KEY"


def test_build_model_keeps_user_key_out_of_environ(monkeypatch):
    """用户 Key 必须按请求显式传入，不能写进进程级环境变量。"""
    litellm_adapter = pytest.importorskip("google.adk.models.lite_llm")
    monkeypatch.setattr(
        model_factory, "settings", SimpleNamespace(google_api_key="", openai_api_key="")
    )
    before = dict(os.environ)

    model = model_factory.build_model(_config(provider="deepseek", api_key="sk-user-secret"))

    assert isinstance(model, litellm_adapter.LiteLlm)
    assert model._additional_args.get("api_key") == "sk-user-secret"
    assert dict(os.environ) == before, "build_model 不应修改进程环境变量"


def test_build_model_passes_base_url_explicitly(monkeypatch):
    litellm_adapter = pytest.importorskip("google.adk.models.lite_llm")
    monkeypatch.setattr(
        model_factory, "settings", SimpleNamespace(google_api_key="", openai_api_key="")
    )

    model = model_factory.build_model(
        _config(provider="deepseek", api_key="k", base_url="http://127.0.0.1:11434/v1")
    )

    assert isinstance(model, litellm_adapter.LiteLlm)
    assert model._additional_args.get("api_base") == "http://127.0.0.1:11434/v1"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "file:///etc/passwd",
        "ftp://example.com",
    ],
)
def test_unsafe_base_url_rejected(base_url):
    with pytest.raises(DomainError):
        model_factory.validate_base_url(base_url)


@pytest.mark.parametrize(
    "base_url",
    ["", "http://127.0.0.1:11434/v1", "https://api.deepseek.com/v1"],
)
def test_safe_base_url_allowed(base_url):
    model_factory.validate_base_url(base_url)


def test_build_model_rejects_unsafe_base_url():
    with pytest.raises(DomainError):
        model_factory.build_model(_config(base_url="http://169.254.169.254/"))


def test_gemini_without_key_or_base_url_defers_to_adk_env(monkeypatch):
    """既无用户 Key 也无自定义端点时仍返回模型名字符串，由 ADK 读环境变量。"""
    monkeypatch.setattr(
        model_factory, "settings", SimpleNamespace(google_api_key="", openai_api_key="")
    )
    assert model_factory.build_model(_config(provider="gemini", model_name="gemini-2.0-flash")) == (
        "gemini-2.0-flash"
    )

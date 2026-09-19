import ipaddress
import logging
from urllib.parse import urlparse

from app.agent_runtime.domain.models import ModelConfig
from app.shared.config import get_settings
from app.shared.exceptions import DomainError

logger = logging.getLogger(__name__)
settings = get_settings()

# provider → 运营者可用环境变量配置的兜底 Key（仅限同名 provider，不跨 provider 复用）
PROVIDER_ENV_KEY = {
    "gemini": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# 云元数据等链路本地地址，禁止作为 base_url（SSRF 防护）
_BLOCKED_HOSTNAMES = frozenset({"metadata", "metadata.google.internal"})


def operator_fallback_key(provider: str) -> str:
    """运营者通过环境变量配置的兜底 Key。

    历史上这里对任意非 gemini provider 都回退到 OPENAI_API_KEY，会把 OpenAI 的
    密钥发送给 DeepSeek 等第三方端点，属于凭据泄露；现在只认同名 provider。
    """
    if provider == "gemini":
        return settings.google_api_key or ""
    if provider == "openai":
        return settings.openai_api_key or ""
    return ""


def resolve_api_key(config: ModelConfig) -> str:
    """解析本次调用应使用的 Key：用户自配优先，其次同名 provider 的运营者兜底。"""
    if config.api_key:
        return config.api_key
    return operator_fallback_key(config.provider)


def validate_base_url(base_url: str) -> None:
    """校验自定义端点，阻断非 http(s) 协议与链路本地/云元数据地址。"""
    if not base_url:
        return
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise DomainError(f"base_url 仅支持 http/https（当前为 {parsed.scheme or '空'}）")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise DomainError("base_url 缺少主机名")
    if host in _BLOCKED_HOSTNAMES:
        raise DomainError("base_url 指向云元数据地址，已拒绝")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if ip.is_link_local:
        raise DomainError("base_url 指向链路本地地址，已拒绝")


def build_model(config: ModelConfig):
    """按配置实例化 ADK 模型对象，凭据按请求显式传入，不写入进程级环境变量。"""
    validate_base_url(config.base_url)
    api_key = resolve_api_key(config)
    if not api_key:
        env_name = PROVIDER_ENV_KEY.get(config.provider, f"{config.provider.upper()}_API_KEY")
        logger.warning(
            "模型 %s/%s 未配置可用 API Key（用户未填写，环境变量 %s 也为空）",
            config.provider,
            config.model_name,
            env_name,
        )

    if config.provider == "gemini":
        from google.adk.models.google_llm import Gemini

        if not api_key and not config.base_url:
            # 无自定义凭据/端点时交由 ADK 按环境变量解析
            return config.model_name
        kwargs: dict = {}
        if api_key:
            kwargs["client_kwargs"] = {"api_key": api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return Gemini(model=config.model_name, **kwargs)

    from google.adk.models.lite_llm import LiteLlm

    call_kwargs: dict = {}
    if api_key:
        call_kwargs["api_key"] = api_key
    if config.base_url:
        call_kwargs["api_base"] = config.base_url
    return LiteLlm(model=f"{config.provider}/{config.model_name}", **call_kwargs)


def default_model_config(user_id: str) -> ModelConfig:
    """未配置任何模型时的兜底：使用环境变量中的 GOOGLE_API_KEY。"""
    return ModelConfig(
        id="env-default",
        user_id=user_id,
        provider="gemini",
        model_name="gemini-2.0-flash",
        api_key=settings.google_api_key,
        label="Gemini (env)",
        is_default=True,
    )

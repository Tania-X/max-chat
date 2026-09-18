import os

from app.agent_runtime.domain.models import ModelConfig
from app.shared.config import get_settings

settings = get_settings()

PROVIDER_ENV_KEY = {
    "gemini": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

PROVIDER_ENV_BASE_URL = {
    "openai": "OPENAI_BASE_URL",
    "deepseek": "DEEPSEEK_API_BASE",
    "openrouter": "OPENROUTER_API_BASE",
}


def apply_model_env(config: ModelConfig) -> None:
    """将模型配置的密钥注入环境变量（LiteLLM / google-genai 从环境读取）。"""
    api_key = config.api_key
    if not api_key:
        api_key = (
            settings.google_api_key if config.provider == "gemini" else settings.openai_api_key
        )
    env_key = PROVIDER_ENV_KEY.get(config.provider, f"{config.provider.upper()}_API_KEY")
    if api_key:
        os.environ[env_key] = api_key
        if config.provider == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
    if config.base_url:
        env_base = PROVIDER_ENV_BASE_URL.get(config.provider)
        if env_base:
            os.environ[env_base] = config.base_url


def build_model(config: ModelConfig):
    """按配置实例化 ADK 模型对象。Gemini 走原生，其他经 LiteLLM 适配。"""
    apply_model_env(config)
    if config.provider == "gemini":
        return config.model_name
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(model=f"{config.provider}/{config.model_name}")


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

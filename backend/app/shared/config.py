from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """全部配置的唯一事实源。新增配置项只需在此声明（带 description），
    .env.example 由 `python -m app.shared.env_example` 生成，CI 强制校验新鲜度。"""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    jwt_secret: str = Field(
        default="change-me-to-a-random-string", description="JWT 签名密钥（生产环境务必更换）"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 签名算法")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, description="JWT 过期时间（分钟）")
    fernet_key: str = Field(
        default="",
        description='Fernet 对称加密密钥（加密存储 API Key），生成：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
    )
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app.db'}", description="数据库连接串"
    )
    google_api_key: str = Field(default="", description="Google Gemini API Key（兜底模型 + 记忆抽取）")
    openai_api_key: str = Field(default="", description="OpenAI API Key（兜底）")
    extractor_model: str = Field(default="gemini-2.0-flash", description="记忆/画像抽取用轻量模型")
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"], description="允许的跨域来源"
    )
    context_message_limit: int = Field(default=50, description="注入上下文的最近消息条数")


@lru_cache
def get_settings() -> Settings:
    return Settings()

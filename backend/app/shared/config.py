from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# JWT 仅允许 HMAC 系列：排除 none（可伪造签名）与非对称算法（易与公钥混淆）
ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class Settings(BaseSettings):
    """全部配置的唯一事实源。新增配置项只需在此声明（带 description），
    .env.example 由 `python -m app.shared.env_example` 生成，CI 强制校验新鲜度。"""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    jwt_secret: str = Field(
        default="",
        description="JWT 签名密钥；留空则首次启动自动生成并持久化到 data/secrets.json（生产环境建议显式配置）",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 签名算法，仅支持 HS256/HS384/HS512")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, description="JWT 过期时间（分钟）")
    fernet_key: str = Field(
        default="",
        description='Fernet 对称加密密钥（加密存储 API Key）；留空则首次启动自动生成并持久化到 data/secrets.json，生成命令：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
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
    allow_stdio_mcp: bool = Field(
        default=False,
        description="是否允许 stdio 传输的 MCP server。stdio 会以本机权限拉起任意子进程，等同于代码执行，仅在完全信任的环境下开启",
    )

    @field_validator("jwt_algorithm")
    @classmethod
    def _validate_jwt_algorithm(cls, value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM 仅支持 {sorted(ALLOWED_JWT_ALGORITHMS)}（当前为 {value!r}）："
                "禁止 none 与非对称算法，避免签名校验被绕过"
            )
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()

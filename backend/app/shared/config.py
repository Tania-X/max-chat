from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    jwt_secret: str = "change-me-to-a-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    fernet_key: str = ""
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app.db'}"

    google_api_key: str = ""
    openai_api_key: str = ""
    extractor_model: str = "gemini-2.0-flash"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    context_message_limit: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()

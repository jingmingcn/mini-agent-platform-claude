"""Application configuration loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Mini-Agent Platform"
    ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    # Database: MySQL in production, SQLite accepted for local dev / tests.
    DATABASE_URL: str = "mysql+pymysql://agent:agent@127.0.0.1:3306/mini_agent?charset=utf8mb4"
    REDIS_URL: str | None = "redis://127.0.0.1:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production-please-32bytes"
    # Fernet key (urlsafe base64, 32 bytes). Derived from SECRET_KEY when empty.
    ENCRYPTION_KEY: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    USER_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_ALGORITHM: str = "HS256"

    # Initial super admin (created by init script)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Admin@123456"

    # WeChat mini program
    WECHAT_APPID: str | None = None
    WECHAT_SECRET: str | None = None
    # When true and WECHAT_APPID is empty, /auth/wechat/login accepts any code and
    # creates a dev user. NEVER enable in production.
    WECHAT_DEV_LOGIN: bool = False

    # Async tasks
    CELERY_ENABLED: bool = False  # False => run document jobs in an in-process thread pool
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Vector DB (Qdrant). Either QDRANT_URL (server) or QDRANT_PATH (embedded, single process only).
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_PATH: str = str(BASE_DIR / "data" / "qdrant")

    # Files
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    MAX_UPLOAD_MB: int = 20
    MAX_CHAT_UPLOAD_MB: int = 10
    MAX_PARSE_CHARS: int = 2_000_000
    MAX_PDF_PAGES: int = 500

    # Chat / LLM
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_RETRIES: int = 2
    DEFAULT_CONTEXT_TOKENS: int = 6000

    # Rate limiting (requests per minute per client)
    RATE_LIMIT_PER_MINUTE: int = 120
    CHAT_RATE_LIMIT_PER_MINUTE: int = 20

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL or "redis://127.0.0.1:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

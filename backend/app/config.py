from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "ShiftWise API"
    debug: bool = True

    database_url: str = "sqlite:///./shiftwise.db"
    async_database_url: str = ""

    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ]

    optimizer_time_limit_seconds: int = 30
    backend_url: str = "https://shiftwise-production.up.railway.app"

    @model_validator(mode="after")
    def derive_async_url(self) -> "Settings":
        if not self.async_database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
                self.database_url = url
            if url.startswith("postgresql://"):
                self.async_database_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            else:
                self.async_database_url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""Application settings, loaded from environment variables / .env.

Kept deliberately small: every other module reads configuration from a single
`Settings` instance (`get_settings()`), never from `os.environ` directly, so
tests can override it by constructing their own `Settings(...)`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./salary.db"
    base_currency: str = "USD"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

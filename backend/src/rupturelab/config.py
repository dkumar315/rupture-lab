from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RuptureLab API"
    environment: Literal["development", "test", "production"] = "development"

    target_url: str = "http://127.0.0.1:9000"
    proxy_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

    proxy_url: str = "http://127.0.0.1:8080"
    experiment_timeout_seconds: float = Field(default=10.0, gt=0, le=300)
    database_url: str = "postgresql+asyncpg://rupturelab@127.0.0.1:5432/rupturelab"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RUPTURELAB_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

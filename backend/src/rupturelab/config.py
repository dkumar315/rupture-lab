from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RuptureLab API"
    environment: str = "development"

    target_url: str = "http://127.0.0.1:9000"
    proxy_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RUPTURELAB_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

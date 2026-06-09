from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema de Zeladoria API"
    environment: str = "development"
    database_url: str = "sqlite:///./zeladoria.db"
    secret_key: str = Field(default="troque-esta-chave-em-producao")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    media_root: Path = Path("media")
    default_admin_email: str = "admin@zeladoria.local"
    default_admin_password: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

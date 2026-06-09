from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Facilities Supervisao API"
    environment: str = "development"
    database_url: str = "sqlite:///./backend/facilities.db"
    secret_key: str = Field(default="troque-esta-chave-em-producao")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    uploads_dir: Path = Path("uploads")
    reports_dir: Path = Path("reports")
    default_admin_email: str = "admin@facilities.local"
    default_admin_password: str = "admin123"
    cors_origins: list[str] = ["*"]
    email_host: str | None = None
    email_port: int = 587
    email_user: str | None = None
    email_password: str | None = None
    billing_client_email: str | None = None
    billing_client_name: str = "Cliente"
    billing_due_date: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

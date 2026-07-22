from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_name: str = "Developer Contact API"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"
    database_path: Path = Path("data/app.db")
    request_log_path: Path = Path("logs/requests.log")
    email_log_path: Path = Path("logs/emails.log")
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    trusted_proxy_ips: Annotated[list[str], NoDecode] = []
    rate_limit_requests: int = Field(default=5, ge=1, le=1000)
    rate_limit_window_seconds: int = Field(default=3600, ge=1, le=86400)
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    ai_timeout_seconds: float = Field(default=8, gt=0, le=60)
    email_mode: str = "log"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@example.com"
    smtp_from_name: str = "Developer Portfolio"
    owner_email: str = "owner@example.com"

    @field_validator("allowed_origins", "trusted_proxy_ips", mode="before")
    @classmethod
    def parse_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("email_mode")
    @classmethod
    def validate_email_mode(cls, value: str) -> str:
        value = value.lower()
        if value not in {"log", "smtp"}:
            raise ValueError("EMAIL_MODE must be 'log' or 'smtp'")
        return value

    def ensure_directories(self) -> None:
        for path in (self.database_path, self.request_log_path, self.email_log_path):
            path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

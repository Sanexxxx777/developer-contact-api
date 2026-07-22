from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "app.db",
        request_log_path=tmp_path / "requests.log",
        email_log_path=tmp_path / "emails.log",
        rate_limit_requests=5,
        rate_limit_window_seconds=3600,
        email_mode="log",
        openai_api_key=None,
    )


@pytest.fixture
def client(settings: Settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_payload() -> dict[str, str]:
    return {
        "name": "Alex Ivanov",
        "phone": "+7 999 123-45-67",
        "email": "alex@example.com",
        "comment": "I would like to discuss a new backend project.",
    }

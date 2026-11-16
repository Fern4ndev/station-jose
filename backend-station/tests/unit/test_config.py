"""Configuration validation tests."""

from pathlib import Path

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", JWT_SECRET_KEY="too-short")


def test_production_rejects_debug_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a" * 32,
            DEBUG=True,
            CORS_ORIGINS="*",
        )


def test_cors_origins_accept_comma_separated_values() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:4200, https://example.test")

    assert settings.cors_origins == ["http://localhost:4200", "https://example.test"]


def test_cors_origins_from_env_file_accept_comma_separated_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.cors_origins == ["http://localhost:4200", "http://127.0.0.1:4200"]

"""Configuration validation tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret_key="too-short")


def test_cors_origins_accept_comma_separated_values() -> None:
    settings = Settings(cors_origins="http://localhost:4200, https://example.test")

    assert settings.cors_origins == ["http://localhost:4200", "https://example.test"]

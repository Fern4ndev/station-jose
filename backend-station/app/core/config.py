"""Typed environment configuration."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "San Jose Fuel Control API"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    timezone: str = "America/Lima"

    database_url: str = (
        "postgresql+psycopg://user:password@localhost:5432/san_jose_db"
    )

    jwt_secret_key: SecretStr = SecretStr("development-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: Annotated[int, Field(gt=0, le=1440)] = 30
    jwt_issuer: str = "san-jose-api"

    cors_origins: list[str] = ["http://localhost:4200"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    ocr_enabled: bool = True
    ocr_max_upload_bytes: Annotated[int, Field(gt=0)] = 10_485_760
    ocr_max_pdf_pages: Annotated[int, Field(gt=0)] = 20
    ocr_timeout_seconds: Annotated[int, Field(gt=0)] = 60
    ocr_temp_dir: str = "/tmp/san-jose-ocr"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_v1_prefix must start with / and not end with /")
        return value

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.app_env == "production" and len(self.jwt_secret_key.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached process settings instance."""
    return Settings()

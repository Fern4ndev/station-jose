"""Typed environment configuration."""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlparse

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

    APP_NAME: str = "San Jose Fuel Control API"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "America/Lima"

    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/sanjose"

    JWT_SECRET_KEY: SecretStr = SecretStr("development-only-change-me")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Annotated[int, Field(gt=0, le=1440)] = 30
    JWT_ISSUER: str = "san-jose-api"

    CORS_ORIGINS: str = "http://localhost:4200"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    OCR_ENABLED: bool = True
    OCR_MAX_UPLOAD_BYTES: Annotated[int, Field(gt=0)] = 10_485_760
    OCR_MAX_PDF_PAGES: Annotated[int, Field(gt=0)] = 20
    OCR_TIMEOUT_SECONDS: Annotated[int, Field(gt=0)] = 60
    OCR_TEMP_DIR: str = "/tmp/san-jose-ocr"
    REPORT_MAX_EXPORT_ROWS: Annotated[int, Field(gt=0)] = 10_000

    @field_validator("API_V1_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("API_V1_PREFIX must start with / and not end with /")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if not self.is_production:
            return self
        if len(self.JWT_SECRET_KEY.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production")
        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        origins = self.cors_origins
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins in production")
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS_ORIGINS contains an invalid origin")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached process settings instance."""
    return Settings()

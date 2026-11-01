"""Configuración de la aplicación leída de variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — el .env vive junto al proyecto, no en el directorio de trabajo.
RAIZ = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Ajustes del backend. Los nombres de campo coinciden con las variables en mayúsculas."""

    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    entorno: str = "desarrollo"
    api_v1_prefix: str = "/api/v1"

    # Conexiones: `vales_app` para la aplicación, `vales_migrador` para el esquema.
    database_url: str
    database_url_test: str = ""
    migrador_url: str = ""
    migrador_url_test: str = ""

    ocr_device: str = "cpu"
    almacenamiento_dir: Path = RAIZ / "almacenamiento"
    frontend_dist: Path = RAIZ.parent / "dist" / "frontend" / "browser"

    jwt_secret_key: str = ""
    recaptcha_secret_key: str = ""
    recaptcha_site_key: str = ""
    recaptcha_umbral_minimo: float = 0.5
    recaptcha_hostname: str = ""

    # Sesión (plan, secciones 4 y 5.2).
    access_token_minutos: int = 10
    recuperacion_token_minutos: int = 15
    # URL del frontend para el enlace del correo de recuperación (P-08).
    frontend_url: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def es_desarrollo(self) -> bool:
        return self.entorno == "desarrollo"

    @model_validator(mode="after")
    def _validar_secretos(self) -> "Settings":
        """Fuera de desarrollo, la clave JWT no puede quedar vacía."""
        if not self.es_desarrollo and not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY es obligatoria fuera de desarrollo")
        return self


@lru_cache
def obtener_settings() -> Settings:
    """Devuelve una única instancia de la configuración."""
    return Settings()

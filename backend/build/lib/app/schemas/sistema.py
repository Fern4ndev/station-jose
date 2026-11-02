"""Esquemas de salida del módulo de sistema."""

from typing import Literal

from pydantic import BaseModel


class SaludRespuesta(BaseModel):
    """Estado del backend, PostgreSQL y RapidOCR, sin datos sensibles."""

    estado: Literal["ok"]
    base: str
    ocr: str
    version: str


class EnumsRespuesta(BaseModel):
    """Catálogos cerrados del dominio, para que Angular no los repita."""

    roles: list[str]
    permisos: list[str]
    tipos_institucion: list[str]
    estados_institucion: list[str]
    modalidades_numeracion: list[str]
    estados_orden: list[str]
    estados_ocr: list[str]
    metodos_ocr: list[str]
    emisores_vale: list[str]
    estados_vale: list[str]
    tipos_movimiento: list[str]

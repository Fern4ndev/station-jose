"""Esquemas Pydantic del módulo Instituciones (plan sección 5.6).

El RUC es obligatorio (varchar(11) NOT NULL en `0001`) y viaja como texto
de exactamente 11 dígitos; la verificación del dígito la hace el servicio
con [app.core.ruc][] (INS-01). Los montos viajan como cadena exacta.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.dominio import MODALIDADES_NUMERACION, TIPOS_INSTITUCION


def _ruc_limpio(valor: str) -> str:
    texto = valor.strip()
    if not texto.isdigit() or len(texto) != 11:
        raise ValueError("El RUC debe tener exactamente 11 dígitos.")
    return texto


def _texto_recortado_no_vacio(valor: str) -> str:
    texto = valor.strip()
    if not texto:
        raise ValueError("El campo no puede quedar vacío.")
    return texto


class InstitucionEntrada(BaseModel):
    """INS-01: datos obligatorios + modalidad por defecto."""

    nombre: str = Field(min_length=3, max_length=250)
    ruc: str
    direccion: str | None = Field(default=None, max_length=300)
    telefono: str | None = Field(default=None, max_length=30)
    correo: EmailStr | None = None
    representante: str | None = Field(default=None, max_length=150)
    tipo: str = "publica"
    modalidad_numeracion: str = "no_aplica"

    @field_validator("nombre", "representante")
    @classmethod
    def texto_recortado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _texto_recortado_no_vacio(valor)

    @field_validator("ruc")
    @classmethod
    def ruc_valido(cls, valor: str) -> str:
        return _ruc_limpio(valor)

    @field_validator("tipo")
    @classmethod
    def tipo_en_lista(cls, valor: str) -> str:
        if valor not in TIPOS_INSTITUCION:
            raise ValueError(f"tipo debe ser uno de {', '.join(TIPOS_INSTITUCION)}.")
        return valor

    @field_validator("modalidad_numeracion")
    @classmethod
    def modalidad_en_lista(cls, valor: str) -> str:
        if valor not in MODALIDADES_NUMERACION:
            raise ValueError(
                f"modalidad_numeracion debe ser uno de {', '.join(MODALIDADES_NUMERACION)}."
            )
        return valor


class InstitucionEditar(BaseModel):
    """INS-04: edición parcial; solo se aplican los campos enviados."""

    nombre: str | None = Field(default=None, min_length=3, max_length=250)
    ruc: str | None = None
    direccion: str | None = Field(default=None, max_length=300)
    telefono: str | None = Field(default=None, max_length=30)
    correo: EmailStr | None = None
    representante: str | None = Field(default=None, max_length=150)
    tipo: str | None = None
    modalidad_numeracion: str | None = None

    @field_validator("nombre", "representante")
    @classmethod
    def texto_recortado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _texto_recortado_no_vacio(valor)

    @field_validator("ruc")
    @classmethod
    def ruc_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _ruc_limpio(valor)

    @field_validator("tipo")
    @classmethod
    def tipo_en_lista(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in TIPOS_INSTITUCION:
            raise ValueError(f"tipo debe ser uno de {', '.join(TIPOS_INSTITUCION)}.")
        return valor

    @field_validator("modalidad_numeracion")
    @classmethod
    def modalidad_en_lista(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in MODALIDADES_NUMERACION:
            raise ValueError(
                f"modalidad_numeracion debe ser uno de {', '.join(MODALIDADES_NUMERACION)}."
            )
        return valor


class InstitucionSalida(BaseModel):
    """INS-03: fila como la ve el listado."""

    id: int
    nombre: str
    ruc: str
    tipo: str
    modalidad_numeracion: str
    estado: str
    creado_en: datetime
    actualizado_en: datetime


class InstitucionesLista(BaseModel):
    """INS-03: página del listado con el total para paginar."""

    items: list[InstitucionSalida]
    total: int
    pagina: int
    por_pagina: int


class InstitucionDetalle(BaseModel):
    """INS-03: ficha completa con los resúmenes de órdenes."""

    id: int
    nombre: str
    ruc: str
    direccion: str | None
    telefono: str | None
    correo: str | None
    representante: str | None
    tipo: str
    modalidad_numeracion: str
    estado: str
    creado_en: datetime
    actualizado_en: datetime
    ordenes: int
    presupuesto_total: str
    vales_vigentes: int
    saldo_vigente_soles: str
    consumo_mes_soles: str


class RespuestaInactivada(BaseModel):
    """INS-06/07: confirmación de la baja o reactivación lógica."""

    id: int
    estado: str


class VerificacionRuc(BaseModel):
    """INS-01/OCR-08: verificación del RUC para la validación en vivo."""

    ruc: str
    valido: bool
    institucion: "InstitucionSalida | None" = None

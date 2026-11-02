"""Esquemas Pydantic del módulo Usuarios (sección 5.3)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UsuarioCrear(BaseModel):
    """USR-01: alta del usuario; la contraseña la genera el backend."""

    nombre: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    rol: str


class UsuarioEditar(BaseModel):
    """USR-03/04: edición parcial; solo se aplican los campos enviados."""

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    correo: EmailStr | None = None
    rol: str | None = None


class UsuarioSalida(BaseModel):
    """Fila de usuario visible en listado y detalle."""

    id: int
    nombre: str
    correo: str
    rol: str
    debe_cambiar_password: bool
    creado_en: datetime


class UsuarioLista(BaseModel):
    """USR-02: listado paginado."""

    items: list[UsuarioSalida]
    total: int
    pagina: int
    por_pagina: int


class UsuarioConClaveTemporal(BaseModel):
    """USR-01/06: la contraseña temporal se entrega solo en esta respuesta."""

    id: int
    nombre: str
    correo: str
    rol: str
    password_temporal: str

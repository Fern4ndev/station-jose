"""Esquemas Pydantic del módulo Órdenes de compra (plan sección 5.7).

El presupuesto viaja como cadena exacta (`"1500.00"`): Decimal en la base,
nunca float (plan sección 1). La serie es opcional y completa; la modalidad
de la institución decide si la acepta.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core import dinero

CAMPOS_NUMERO = {"numero": "El número de orden no es un entero del rango válido."}


def _ano_valido(valor: str) -> str:
    texto = valor.strip()
    try:
        fecha = date.fromisoformat(texto)
    except ValueError as exc:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
    if fecha.isoformat() != texto:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.")
    return texto


class OrdenCrear(BaseModel):
    """ORD-01: alta con institución, presupuesto y fecha; estado por defecto borrador."""

    institucion_id: int
    numero: int | None = Field(default=None, ge=1)
    fecha_emision: str
    presupuesto_soles: str
    observaciones: str | None = Field(default=None, max_length=500)
    combustible_id: int | None = None
    serie_desde: int | None = Field(default=None, ge=1)
    serie_hasta: int | None = Field(default=None, ge=1)
    estado: str = "borrador"
    confirmar_duplicado: bool = False

    @field_validator("fecha_emision")
    @classmethod
    def fecha_iso(cls, valor: str) -> str:
        return _ano_valido(valor)

    @field_validator("presupuesto_soles")
    @classmethod
    def presupuesto_valido(cls, valor: str) -> str:
        try:
            monto = dinero.monto(valor)
        except dinero.ErrorNumero as exc:
            raise ValueError("El presupuesto debe ser un monto con hasta 2 decimales.") from exc
        if not dinero.es_positivo(monto):
            raise ValueError("El presupuesto debe ser mayor que cero (RN-01).")
        return str(monto)

    @field_validator("estado")
    @classmethod
    def estado_inicial(cls, valor: str) -> str:
        if valor not in ("borrador", "vigente"):
            raise ValueError("El estado inicial debe ser borrador o vigente.")
        return valor

    @field_validator("observaciones")
    @classmethod
    def observaciones_recortadas(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        texto = valor.strip()
        return texto or None


class OrdenEditar(BaseModel):
    """ORD-03: edición parcial; con vales ya emitidos solo observaciones."""

    presupuesto_soles: str | None = None
    observaciones: str | None = Field(default=None, max_length=500)
    serie_desde: int | None = Field(default=None, ge=1)
    serie_hasta: int | None = Field(default=None, ge=1)
    combustible_id: int | None = None
    confirmar_duplicado: bool = False

    @field_validator("presupuesto_soles")
    @classmethod
    def presupuesto_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        try:
            monto = dinero.monto(valor)
        except dinero.ErrorNumero as exc:
            raise ValueError("El presupuesto debe ser un monto con hasta 2 decimales.") from exc
        if not dinero.es_positivo(monto):
            raise ValueError("El presupuesto debe ser mayor que cero (RN-01).")
        return str(monto)

    @field_validator("observaciones")
    @classmethod
    def observaciones_recortadas(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        texto = valor.strip()
        return texto or None


class OrdenSalida(BaseModel):
    """ORD-05: fila del listado. El número es el texto exacto (ORD-02)."""

    id: int
    institucion_id: int
    razon_social: str
    anio: int
    numero: str
    fecha_emision: date
    presupuesto_soles: str
    estado: str
    combustible_id: int | None
    creado_en: datetime


class OrdenesLista(BaseModel):
    """ORD-05: página del listado con el total para paginar."""

    items: list[OrdenSalida]
    total: int
    pagina: int
    por_pagina: int


class ValeResumen(BaseModel):
    """Vale de la ficha de la orden en detalle ORD-06."""

    id: int
    emisor: str
    numero_estacion: str | None
    numero_entidad: str | None
    estado: str
    saldo: str
    valor_soles: str
    fecha_emision: date


class OrdenDetalle(BaseModel):
    """ORD-06/ORD-09: ficha con totales derivados (RN-03).

    Todos los montos viajan como cadena exacta (plan sección 1): Decimal en
    la base, nunca float.
    """

    id: int
    institucion_id: int
    razon_social: str
    institucion_ruc: str | None
    anio: int
    numero: str
    fecha_emision: date
    presupuesto_soles: str
    observaciones: str | None
    estado: str
    serie_desde: int | None
    serie_hasta: int | None
    combustible_id: int | None
    archivo_path: str | None
    archivo_tipo: str | None
    archivo_tamano: int | None
    creado_en: datetime
    actualizado_en: datetime
    total_emitido_soles: str
    total_emitido_galones: str
    presupuesto_restante_soles: str
    total_consumido_soles: str
    cantidad_vales: int
    vales: list[ValeResumen]


class OrdenEstado(BaseModel):
    """ORD-07/09/10: respuesta de las transiciones."""

    id: int
    estado: str
    motivo_anulacion: str | None = None


class AnulacionEntrada(BaseModel):
    """ORD-09: motivo obligatorio (RN-09/ORD-09)."""

    motivo: str = Field(min_length=3, max_length=500)

    @field_validator("motivo")
    @classmethod
    def motivo_recortado(cls, valor: str) -> str:
        texto = valor.strip()
        if len(texto) < 3:
            raise ValueError("El motivo es obligatorio y debe tener al menos 3 caracteres.")
        return texto


class ArchivoAdjunto(BaseModel):
    """ORD-04: confirmación del documento adjunto."""

    archivo_path: str
    media_type: str
    archivo_tamano: int
    archivo_hash: str


class OrdenSerie(BaseModel):
    """ORD-02b/VAL-15: stock de la serie de la orden (numeración por orden)."""

    serie_desde: int
    serie_hasta: int
    total_rango: int
    usados: list[int]
    disponibles: list[int]


class AdvertenciaDuplicado(BaseModel):
    """ORD-08: respuesta del endpoint de cruce antes de guardar."""

    certificada: bool
    orden: OrdenSalida | None = None

"""Esquemas Pydantic del módulo Vales (plan sección 5.9, Fase 6).

Las montos y cantidades viajan como cadena exacta (`"1500.00"` / `"50.00"`):
Decimal en la base, nunca float (plan sección 1). La emisión recibe la lista
de cantidades y `fecha_vencimiento` opcional (P-02).
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core import dinero


def _fecha_o_vacia(valor: str | None) -> str | None:
    """Fecha `AAAA-MM-DD` opcional; una cadena vacía equivale a None."""
    if valor is None:
        return None
    texto = valor.strip()
    if not texto:
        return None
    try:
        fecha = date.fromisoformat(texto)
    except ValueError as exc:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
    if fecha.isoformat() != texto:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.")
    return texto


class SimulacionEntrada(BaseModel):
    """VAL-01/VAL-03: combustible y cantidades de la vista previa."""

    combustible_id: int
    cantidades: list[str] = Field(min_length=1)

    @field_validator("cantidades")
    @classmethod
    def cantidades_numericas(cls, valores: list[str]) -> list[str]:
        for valor in valores:
            try:
                cantidad = dinero.cantidad(valor)
            except dinero.ErrorNumero as exc:
                raise ValueError(
                    "Cada cantidad debe ser un número con hasta 2 decimales."
                ) from exc
            if not dinero.es_positivo(cantidad):
                raise ValueError("Cada cantidad debe ser mayor que cero.")
        return valores


class SimulacionVale(BaseModel):
    """Vale previsto de la simulación (no guarda nada)."""

    cantidad_galones: str
    valor_soles: str


class SimulacionSalida(BaseModel):
    """CMB-04/VAL-03: precio vigente, presupuesto y techo de galones."""

    orden_compra_id: int
    precio_galon: str
    presupuesto_restante_soles: str
    maximo_galones: str
    vales: list[SimulacionVale]
    total_soles: str


class ValeEstacionEntrada(BaseModel):
    """VAL-01: combustible, vales y vencimiento opcional concentrados."""

    combustible_id: int
    cantidades: list[str] = Field(min_length=1)
    fecha_vencimiento: str | None = Field(default=None, max_length=10)

    _fecha = field_validator("fecha_vencimiento", mode="before")(lambda c, v: _fecha_o_vacia(v))

    @field_validator("cantidades")
    @classmethod
    def cantidades_numericas(cls, valores: list[str]) -> list[str]:
        for valor in valores:
            try:
                cantidad = dinero.cantidad(valor)
            except dinero.ErrorNumero as exc:
                raise ValueError(
                    "Cada cantidad debe ser un número con hasta 2 decimales."
                ) from exc
            if not dinero.es_positivo(cantidad):
                raise ValueError("Cada cantidad debe ser mayor que cero.")
        return valores


class ValeEmitido(BaseModel):
    """Respuesta de cada vale emitido o registrado (VAL-02, VAL-05)."""

    id: int
    numero_estacion: str | None = None
    numero_entidad: str | None = None
    cantidad_inicial: str
    saldo: str
    valor_soles: str
    precio_galon_aplicado: str
    emisor: str
    estado: str


class ValeEntidadEntrada(BaseModel):
    """VAL-05/VAL-15: el número lo entrega la institución (D-02)."""

    numero_entidad: str = Field(min_length=1, max_length=80)
    combustible_id: int
    cantidad: str
    fecha_vencimiento: str | None = None

    @field_validator("numero_entidad")
    @classmethod
    def numero_recortado(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("El número del vale de entidad es obligatorio.")
        return texto

    @field_validator("cantidad")
    @classmethod
    def cantidad_valida(cls, valor: str) -> str:
        try:
            cantidad = dinero.cantidad(valor)
        except dinero.ErrorNumero as exc:
            raise ValueError(
                "La cantidad debe ser un número con hasta 2 decimales."
            ) from exc
        if not dinero.es_positivo(cantidad):
            raise ValueError("La cantidad debe ser mayor que cero.")
        return valor


class ValeRow(BaseModel):
    """VAL-06: fila del listado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    emisor: str
    numero_estacion: str | None = None
    numero_entidad: str | None = None
    institucion_id: int
    razon_social: str
    orden_id: int
    orden_numero: str | None = None
    orden_anio: int | None = None
    combustible_id: int
    combustible_nombre: str
    cantidad_inicial: str
    consumido: str
    saldo: str
    valor_soles: str
    estado: str
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    creado_en: datetime | None = None


class ValeDetalle(BaseModel):
    """VAL-07/VAL-08: ficha completa del vale con derivados."""

    id: int
    emisor: str
    numero_estacion: str | None = None
    numero_entidad: str | None = None
    orden_compra_id: int
    orden_numero: str | None = None
    orden_anio: int | None = None
    institucion_id: int
    institucion: str
    institucion_ruc: str | None = None
    combustible_id: int
    combustible_nombre: str
    cantidad_inicial: str
    consumido: str
    saldo: str
    precio_galon_aplicado: str
    valor_soles: str
    valor_comprometido_soles: str | None = None
    estado: str
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    veces_impreso: int | None = None
    creado_por: int | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None


class ValesLista(BaseModel):
    """VAL-06: página del listado con el total para paginar."""

    items: list[ValeRow]
    total: int
    pagina: int
    por_pagina: int


class AlertasSalida(BaseModel):
    """VAL-13: saldo bajo y próximos a vencer según CFG-01."""

    saldo_bajo: list[dict]
    por_vencer: list[dict]


class MovimientoSalida(BaseModel):
    """CON-12: movimiento de la línea de tiempo."""

    id: int
    tipo: str
    variacion: str
    saldo_posterior: str
    cantidad_galones: str | None = None
    importe_soles: str | None = None
    motivo: str | None = None
    placa: str | None = None
    conductor: str | None = None
    fecha_local: str | None = None
    creado_en: datetime | None = None
    usuario: str | None = None


class ImpresionSalida(BaseModel):
    """VAL-12: datos de impresión con la marca de duplicado."""

    id: int
    emisor: str
    numero_estacion: str | None = None
    numero_entidad: str | None = None
    estado: str
    veces_impreso: int
    es_duplicado: bool

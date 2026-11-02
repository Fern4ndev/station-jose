"""Esquemas Pydantic del módulo Consumos (plan sección 5.10, Fase 7).

El despacho viaja con `token_operacion` (UUID): el índice único de
`movimientos_vale.token_operacion` garantiza que un reenvío devuelva el
movimiento original y no duplique el descuento (CON-02/CON-08). La cantidad
entra en galones o como importe en soles, exactamente uno; montos y
cantidades viajan como cadena exacta (plan sección 1).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core import dinero


def _a_cantidad_o_error(valor: str, campo: str) -> str:
    """Cantidad/importe con hasta 2 decimales y mayor que cero."""
    try:
        numero = dinero.cantidad(valor)
    except dinero.ErrorNumero as exc:
        raise ValueError(
            f"{campo} debe ser un número con hasta 2 decimales."
        ) from exc
    if not dinero.es_positivo(numero):
        raise ValueError(f"{campo} debe ser mayor que cero.")
    return valor


class ConsumoEntrada(BaseModel):
    """CON-01..CON-09: datos del despacho sobre un vale."""

    cantidad_galones: str | None = None
    importe_soles: str | None = None
    token_operacion: uuid.UUID
    combustible_id: int | None = None
    placa: str | None = Field(default=None, max_length=30)
    conductor: str | None = Field(default=None, max_length=150)
    observacion: str | None = Field(default=None, max_length=500)
    fecha_local: str | None = Field(default=None, max_length=10)
    motivo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def cantidad_o_importe(self) -> "ConsumoEntrada":
        """CON-05: exactamente uno de galones o importe en soles."""
        resuelto = False
        for campo, valor in (
            ("cantidad_galones", self.cantidad_galones),
            ("importe_soles", self.importe_soles),
        ):
            if valor is None or not str(valor).strip():
                continue
            if resuelto:
                raise ValueError(
                    "Envié cantidad_galones o importe_soles, no ambos."
                )
            try:
                numero = dinero.a_decimal(valor)
            except dinero.ErrorNumero as exc:
                raise ValueError(
                    f"{campo} debe ser un número con hasta 2 decimales."
                ) from exc
            if not dinero.es_positivo(numero):
                raise ValueError(f"{campo} debe ser mayor que cero.")
            resuelto = True
        if not resuelto:
            raise ValueError("Indica cantidad_galones o importe_soles.")
        return self

    @field_validator("cantidad_galones")
    @classmethod
    def cantidad_valida(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _a_cantidad_o_error(valor, "cantidad_galones")

    @field_validator("importe_soles")
    @classmethod
    def importe_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _a_cantidad_o_error(valor, "importe_soles")


class ConsumoRevertir(BaseModel):
    """CON-11: la reversión de un consumo exige motivo."""

    motivo: str = Field(min_length=3, max_length=500)


class ValeAnular(BaseModel):
    """VAL-10: anulación del vale con motivo obligatorio."""

    motivo: str = Field(min_length=3, max_length=500)


class ValeAjuste(BaseModel):
    """VAL-11/RN-09: variación con signo y motivo obligatorio."""

    variacion: str
    motivo: str = Field(min_length=3, max_length=500)

    @field_validator("variacion")
    @classmethod
    def variacion_con_signo(cls, valor: str) -> str:
        try:
            numero = dinero.a_decimal(valor)
        except dinero.ErrorNumero as exc:
            raise ValueError(
                "La variación debe ser un número con hasta 2 decimales."
            ) from exc
        if numero == 0:
            raise ValueError("La variación no puede ser cero.")
        return valor


class VencimientosSalida(BaseModel):
    """VAL-09: resultado del proceso de vencimientos."""

    vencidos: int


class MovimientoSalida(BaseModel):
    """CON-01: movimiento registrado o el original del reenvío."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vale_id: int
    tipo: str
    variacion: str
    saldo_posterior: str
    cantidad_galones: str | None = None
    precio_galon: str | None = None
    importe_soles: str | None = None
    motivo: str | None = None
    placa: str | None = None
    conductor: str | None = None
    token_operacion: str | None = None
    fecha_local: str | None = None
    creado_en: datetime | None = None
    usuario: str
    saldo_vale: str | None = None


class Comprobante(BaseModel):
    """CON-10: datos para el comprobante imprimible."""

    movimiento_id: int
    tipo: str
    fecha_local: str | None = None
    creado_en: datetime | None = None
    vale_id: int
    numero_estacion: str | None = None
    numero_entidad: str | None = None
    emisor: str | None = None
    institucion: str | None = None
    orden_numero: str | None = None
    orden_anio: int | None = None
    combustible: str | None = None
    cantidad_galones: str | None = None
    precio_galon: str | None = None
    importe_soles: str | None = None
    saldo_posterior: str
    saldo_vale: str | None = None
    placa: str | None = None
    conductor: str | None = None
    usuario: str
    estacion: str | None = None

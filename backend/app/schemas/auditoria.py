"""Esquemas Pydantic de Auditoría e integridad (plan sección 5.13, Fase 8).

La bitácora muestra el antes y el después de cada acción (AUD-03); el
historial repite esas mismas filas para un registro concreto (AUD-04). Los
saldos de una diferencia viajan como cadena exacta, igual que el resto de
montos del sistema (plan, sección 1).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EntradaBitacora(BaseModel):
    """AUD-03: una acción registrada, con su usuario y sus valores."""

    id: int
    app_user_id: int | None = None
    usuario: str | None = None
    accion: str
    entidad: str
    entidad_id: str | None = None
    antes: dict[str, Any] | None = None
    despues: dict[str, Any] | None = None
    ip: str | None = None
    user_agent: str | None = None
    creado_en: datetime


class Bitacora(BaseModel):
    """AUD-03: página de la bitácora con el total para paginar."""

    items: list[EntradaBitacora]
    total: int
    pagina: int
    por_pagina: int


class Historial(BaseModel):
    """AUD-04: línea de tiempo de un registro concreto."""

    entidad: str
    entidad_id: int
    items: list[EntradaBitacora]


class VerificacionFila(BaseModel):
    """AUD-05: una corrida de la verificación de saldos."""

    id: int
    ejecutada_por: int | None = None
    ejecutada_por_nombre: str | None = None
    vales_revisados: int
    diferencias: int
    creado_en: datetime


class Verificaciones(BaseModel):
    """AUD-05: historial paginado de verificaciones."""

    items: list[VerificacionFila]
    total: int
    pagina: int
    por_pagina: int


class UltimaVerificacion(BaseModel):
    """AUD-05: última corrida y cuántas diferencias siguen sin revisar."""

    verificacion: VerificacionFila | None = None
    diferencias_pendientes: int


class DiferenciaFila(BaseModel):
    """AUD-06: un descuadre entre el saldo guardado y sus movimientos."""

    id: int
    verificacion_id: int
    vale_id: int
    numero_estacion: str | None = None
    emisor: str | None = None
    saldo_almacenado: str
    saldo_recalculado: str
    diferencia: str
    revisada: bool
    revisada_por: int | None = None
    revisada_por_nombre: str | None = None
    revisada_en: datetime | None = None
    comentario: str | None = None
    creado_en: datetime


class Diferencias(BaseModel):
    """AUD-06: página de diferencias con el total para paginar."""

    items: list[DiferenciaFila]
    total: int
    pagina: int
    por_pagina: int


class RevisionEntrada(BaseModel):
    """AUD-06: la revisión exige un comentario que explique la decisión."""

    comentario: str = Field(min_length=1, max_length=500)

    @field_validator("comentario")
    @classmethod
    def comentario_con_contenido(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("Indique el motivo de la revisión.")
        return texto


class IndicadoresPanel(BaseModel):
    """REP-01: métricas operativas del mes y advertencia de integridad."""

    ordenes_mes: int = 0
    vales_activos: int = 0
    galones_mes: str = "0.00"
    vales_saldo_bajo: int = 0
    vales_por_vencer: int = 0
    diferencias_sin_revisar: int | None = None

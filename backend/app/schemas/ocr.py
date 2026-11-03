"""Contratos de la API de extracción y revisión de órdenes OCR."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ordenes import OrdenCrear


class CampoOcr(BaseModel):
    clave: str
    valor: str
    bruto: str
    confianza: float = Field(ge=0, le=1)
    requiere_revision: bool


class InstitucionSugerida(BaseModel):
    nombre: str | None = None
    ruc: str
    confianza: float = Field(ge=0, le=1)
    institucion_id: int | None = None
    institucion_registrada: bool = False


class PartidaCombustibleOcr(BaseModel):
    codigo: str | None = None
    cantidad: str | None = None
    unidad_medida: str | None = None
    descripcion: str | None = None
    precio_unitario: str | None = None
    precio_total: str | None = None
    evidencia: str | None = None


class ProveedorOcr(BaseModel):
    razon_social: str | None = None
    ruc: str | None = None
    direccion: str | None = None


class DatosOrdenOcr(BaseModel):
    numero_orden: str | None = None
    numero_siaf: str | None = None
    fecha: str | None = None
    fecha_dia_mes_anio: str | None = None
    fecha_correccion_ocr: str | None = None
    proveedor: ProveedorOcr | None = None
    sede_estacion: str | None = None
    unidad_ejecutora: str | None = None
    codigo_unidad_ejecutora: str | None = None
    ruc_unidad_ejecutora: str | None = None
    partidas_combustible: list[PartidaCombustibleOcr] = Field(default_factory=list)
    partidas_pendientes_revision: list[dict[str, str]] = Field(default_factory=list)
    advertencias: list[str] = Field(default_factory=list)


class ExtraccionSalida(BaseModel):
    id: int
    estado: str
    metodo: str | None = None
    campos: list[CampoOcr] = Field(default_factory=list)
    institucion_sugerida: InstitucionSugerida | None = None
    datos_orden: DatosOrdenOcr | None = None
    advertencias: list[str] = Field(default_factory=list)
    error_codigo: str | None = None
    error_detalle: str | None = None
    paginas: int | None = None
    tiempo_ms: int | None = None
    version_pipeline: str | None = None
    creado_en: datetime


class ConfirmarExtraccion(BaseModel):
    datos_revisados: bool
    orden: OrdenCrear
    datos_orden: DatosOrdenOcr | None = None


class ConfirmacionSalida(BaseModel):
    extraccion_id: int
    orden_id: int
    estado: str = "confirmada"


class HistorialOcrItem(BaseModel):
    id: int
    app_user_id: int
    archivo_nombre: str
    estado: str
    metodo: str | None
    confianza_promedio: float | None
    tiempo_ms: int | None
    error_codigo: str | None
    orden_compra_id: int | None
    creado_en: datetime


class HistorialOcr(BaseModel):
    items: list[HistorialOcrItem]
    total: int
    pagina: int
    por_pagina: int


class PrecisionCampo(BaseModel):
    evaluados: int
    corregidos: int
    precision: float | None


class PrecisionOcr(BaseModel):
    total_confirmadas: int
    campos: dict[str, PrecisionCampo]


class DescartarSalida(BaseModel):
    id: int
    estado: str = "descartada"

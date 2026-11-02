"""Esquemas Pydantic del módulo Combustibles y precios (plan sección 5.5).

Los montos viajan como cadena exacta (`"15.50"`): Decimal en la base, nunca
float (plan sección 1, `core/dinero.py`).
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core import dinero


class CombustibleCrear(BaseModel):
    """CMB-01: registro del tipo; el nombre no se repite."""

    nombre: str = Field(min_length=2, max_length=80)

    @field_validator("nombre")
    @classmethod
    def nombre_recortado(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("El nombre no puede quedar vacío.")
        return texto


class CombustibleEditar(BaseModel):
    """CMB-01: edición parcial; solo se aplican los campos enviados."""

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    activo: bool | None = None


class PrecioSalida(BaseModel):
    """Precio con su fecha de vigencia y quién lo registró."""

    id: int
    precio_galon: str
    vigente_desde: str
    creado_en: datetime
    registrado_por: str | None


class PrecioEntrada(BaseModel):
    """CMB-02: precio nuevo por fecha de vigencia (sin editar ni borrar)."""

    precio_galon: str
    vigente_desde: str

    @field_validator("precio_galon")
    @classmethod
    def precio_valido(cls, valor: str) -> str:
        try:
            precio = dinero.monto(valor)
        except dinero.ErrorNumero as exc:
            raise ValueError("El precio debe ser un número con hasta 2 decimales.") from exc
        if not dinero.es_positivo(precio):
            raise ValueError("El precio por galón debe ser mayor que cero.")
        return str(precio)

    @field_validator("vigente_desde")
    @classmethod
    def fecha_iso(cls, valor: str) -> str:
        texto = valor.strip()
        try:
            from datetime import date

            date.fromisoformat(texto)
        except ValueError as exc:
            raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
        return texto


class PrecioRegistrado(BaseModel):
    """Respuesta de POST de precio con lo registrado."""

    id: int
    combustible_id: int
    precio_galon: str
    vigente_desde: str
    creado_en: datetime | None = None


class PrecioVigente(BaseModel):
    """CMB-03: precio vigente con su vigencia."""

    precio_galon: str
    vigente_desde: str


class CombustibleSalida(BaseModel):
    """CMB-01/03: fila del catálogo con el precio vigente si existe."""

    id: int
    nombre: str
    activo: bool
    creado_en: datetime
    precio_vigente: PrecioVigente | None = None


class CombustiblesLista(BaseModel):
    """Catálogo completo, filtrado opcionalmente por estado."""

    items: list[CombustibleSalida]


class HistoricoPrecios(BaseModel):
    """CMB-03: histórico completo, del más reciente al más antiguo."""

    items: list[PrecioSalida]

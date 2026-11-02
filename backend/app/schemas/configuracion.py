"""Esquemas Pydantic del módulo Configuración (plan sección 5.4)."""

from pydantic import BaseModel, EmailStr, Field


class ParametroDetalle(BaseModel):
    """CFG-01: parámetro con valor vigente y su contrato de validación."""

    clave: str
    valor: str
    tipo: str
    defecto: str
    minimo: float | None
    maximo: float | None
    descripcion: str


class ParametrosLista(BaseModel):
    """CFG-01: catálogo completo de parámetros del sistema."""

    items: list[ParametroDetalle]


class ParametrosEntrada(BaseModel):
    """CFG-01: conjunto a guardar. La llave es la clave del parámetro."""

    valores: dict[str, str] = Field(min_length=1)


class ParametrosGuardados(BaseModel):
    """CFG-01: valores vigentes tras aplicar el conjunto."""

    valores: dict[str, str]


class EstacionDatos(BaseModel):
    """CFG-02: datos visibles en comprobantes y vistas de impresión."""

    nombre: str = Field(min_length=3, max_length=200)
    ruc: str | None = Field(default=None, pattern=r"^[0-9]{11}$")
    direccion: str | None = Field(default=None, max_length=300)
    telefono: str | None = Field(default=None, max_length=30)
    correo: EmailStr | None = None


class EstacionSalida(BaseModel):
    """CFG-02: ficha de la estación, incluida la ruta del logo si la hay."""

    nombre: str
    ruc: str | None
    direccion: str | None
    telefono: str | None
    correo: str | None
    logo_path: str | None


class LogoSubido(BaseModel):
    """CFG-02: confirmación de la subida con el tipo real del contenido."""

    media_type: str
    logo_path: str

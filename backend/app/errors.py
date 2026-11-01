"""Errores del dominio y manejadores HTTP con el formato del plan (sección 4).

Toda respuesta de error es `{ "codigo", "mensaje", "detalles" }` con el estado
HTTP adecuado; el manejador general nunca expone trazas al cliente.
"""

import logging
from typing import Any

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ErrorHttp

logger = logging.getLogger("app.errores")


class ErrorDominio(Exception):
    """Error de regla de negocio con código estable para el frontend.

    Ejemplo: `raise ErrorDominio(409, "SALDO_INSUFICIENTE", "El saldo no alcanza para el consumo.")`
    """

    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensaje: str,
        detalles: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or {}
        super().__init__(mensaje)


# Códigos del plan (sección 4). La lista crece con cada fase; el frontend
# puede mostrarse por código sin depender del mensaje.
CODIGOS_VALIDADOS = frozenset(
    {
        "CREDENCIALES_INVALIDAS",
        "CUENTA_BLOQUEADA",
        "CAMBIO_PASSWORD_OBLIGATORIO",
        "SESION_EXPIRADA",
        "TOKEN_INVALIDO",
        "SIN_PERMISO",
        "ULTIMO_ADMINISTRADOR",
        "RUC_DUPLICADO",
        "ORDEN_DUPLICADA",
        "ORDEN_POSIBLE_DUPLICADA",
        "ESTADO_INVALIDO",
        "ORDEN_CON_CONSUMOS",
        "SIN_PRECIO_VIGENTE",
        "PRESUPUESTO_EXCEDIDO",
        "NUMERO_ENTIDAD_DUPLICADO",
        "NUMERO_FUERA_DE_SERIE",
        "SERIE_AGOTADA",
        "VALE_NO_CONSUMIBLE",
        "SALDO_INSUFICIENTE",
        "COMBUSTIBLE_DISTINTO",
        "CONSUMO_YA_REVERTIDO",
        "AJUSTE_NEGATIVO",
        "ARCHIVO_NO_PERMITIDO",
        "ARCHIVO_DEMASIADO_GRANDE",
        "OCR_NO_DISPONIBLE",
        "OCR_OCUPADO",
        "DOCUMENTO_ILEGIBLE",
        "EXTRACCION_NO_CONFIRMABLE",
    }
)

CODIGO_VALIDACION = "VALIDACION_INVALIDA"
CODIGO_ERROR_INTERNO = "ERROR_INTERNO"
MENSAJE_ERROR_INTERNO = "Error interno del servidor. Revise los registros del backend."

# Códigos genéricos que no vienen del dominio sino del enrutamiento HTTP.
CODIGO_RECURSO_NO_ENCONTRADO = "RECURSO_NO_ENCONTRADO"
CODIGO_METODO_NO_PERMITIDO = "METODO_NO_PERMITIDO"
CODIGO_PETICION_INVALIDA = "PETICION_INVALIDA"


def respuesta(
    status_code: int, codigo: str, mensaje: str, detalles: dict[str, Any] | None = None
) -> JSONResponse:
    """Construye la respuesta de error estándar del plan."""
    return JSONResponse(
        status_code=status_code,
        content={"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}},
    )


def manejar_error_dominio(_aplicacion: FastAPI, exc: ErrorDominio) -> JSONResponse:
    return respuesta(exc.status_code, exc.codigo, exc.mensaje, exc.detalles)


def _mensaje_por_campo(exc: RequestValidationError) -> dict[str, list[str]]:
    """Agrupa los mensajes de validación por campo, para la vista de formulario."""
    errores: dict[str, list[str]] = {}
    for error in exc.errors():
        ubicacion = [str(parte) for parte in error["loc"]]
        if ubicacion and ubicacion[0] in ("body", "query"):
            ubicacion = ubicacion[1:]
        campo = ".".join(ubicacion)
        mensaje = error.get("msg", "valor inválido")
        errores.setdefault(campo, []).append(mensaje)
    return errores


def manejar_validacion(_aplicacion: FastAPI, exc: RequestValidationError) -> JSONResponse:
    return respuesta(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        CODIGO_VALIDACION,
        "Revise los campos marcados.",
        _mensaje_por_campo(exc),
    )


def manejar_error_http(_aplicacion: FastAPI, exc: ErrorHttp) -> JSONResponse:
    """Traduce 404/405 y demás HTTPException al formato estándar del plan."""
    codigo = {
        status.HTTP_404_NOT_FOUND: CODIGO_RECURSO_NO_ENCONTRADO,
        status.HTTP_405_METHOD_NOT_ALLOWED: CODIGO_METODO_NO_PERMITIDO,
    }.get(exc.status_code, CODIGO_PETICION_INVALIDA)
    mensaje = exc.detail if isinstance(exc.detail, str) else "Petición HTTP inválida."
    return respuesta(exc.status_code, codigo, mensaje)


def manejar_error_inesperado(_aplicacion: FastAPI, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado", exc_info=exc)
    return respuesta(
        status.HTTP_500_INTERNAL_SERVER_ERROR, CODIGO_ERROR_INTERNO, MENSAJE_ERROR_INTERNO
    )


def registrar_manejadores(app: FastAPI) -> None:
    """Instala los manejadores estándar sobre la instancia `app`."""
    app.add_exception_handler(ErrorDominio, manejar_error_dominio)
    app.add_exception_handler(ErrorHttp, manejar_error_http)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(Exception, manejar_error_inesperado)

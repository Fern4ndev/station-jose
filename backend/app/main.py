"""Punto de entrada de la API (`fastapi dev`)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.config import obtener_settings
from app.db.sesion import motor
from app.errors import registrar_manejadores
from app.routers import (
    auditoria,
    auth,
    catalogos,
    combustibles,
    configuracion,
    consultas,
    consumos,
    instituciones,
    ocr,
    ordenes,
    panel,
    reportes,
    sistema,
    usuarios,
    vales,
)
from app.web.frontend import registrar_frontend

ajustes = obtener_settings()


@asynccontextmanager
async def ciclo_vida(_: FastAPI) -> AsyncIterator[None]:
    """Cierra el pool de conexiones al apagar la aplicación."""
    yield
    await motor.dispose()


app = FastAPI(
    title="San José API",
    description="Gestión de vales de combustible de la estación de servicio San José.",
    version="0.5.0",
    docs_url="/docs" if ajustes.es_desarrollo else None,
    redoc_url="/redoc" if ajustes.es_desarrollo else None,
    openapi_url="/openapi.json" if ajustes.es_desarrollo else None,
    lifespan=ciclo_vida,
)
registrar_frontend(app)


@app.middleware("http")
async def cabeceras_seguridad(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Aplica cabeceras uniformes a las respuestas del backend y del frontend."""
    respuesta = await call_next(request)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "img-src 'self' data:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'",
    )
    if ajustes.es_desarrollo and request.url.path in {"/docs", "/redoc"}:
        respuesta.headers.pop("Content-Security-Policy", None)
    return respuesta

app.include_router(sistema.router, prefix=ajustes.api_v1_prefix)
app.include_router(auth.router, prefix=ajustes.api_v1_prefix)
app.include_router(catalogos.router, prefix=ajustes.api_v1_prefix)
app.include_router(usuarios.router, prefix=ajustes.api_v1_prefix)
app.include_router(combustibles.router, prefix=ajustes.api_v1_prefix)
app.include_router(configuracion.router, prefix=ajustes.api_v1_prefix)
app.include_router(instituciones.router, prefix=ajustes.api_v1_prefix)
app.include_router(ordenes.router, prefix=ajustes.api_v1_prefix)
app.include_router(ocr.router, prefix=ajustes.api_v1_prefix)
app.include_router(vales.router_emision, prefix=ajustes.api_v1_prefix)
app.include_router(vales.router_vales, prefix=ajustes.api_v1_prefix)
app.include_router(consumos.router, prefix=ajustes.api_v1_prefix)
app.include_router(consultas.router, prefix=ajustes.api_v1_prefix)
app.include_router(reportes.router, prefix=ajustes.api_v1_prefix)
app.include_router(auditoria.router, prefix=ajustes.api_v1_prefix)
app.include_router(panel.router, prefix=ajustes.api_v1_prefix)
registrar_manejadores(app)

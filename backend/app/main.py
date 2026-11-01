"""Punto de entrada de la API (`fastapi dev`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import obtener_settings
from app.db.sesion import motor
from app.errors import registrar_manejadores
from app.routers import (
    auth,
    catalogos,
    combustibles,
    configuracion,
    instituciones,
    ordenes,
    sistema,
    usuarios,
    vales,
)

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
    lifespan=ciclo_vida,
)

app.include_router(sistema.router, prefix=ajustes.api_v1_prefix)
app.include_router(auth.router, prefix=ajustes.api_v1_prefix)
app.include_router(catalogos.router, prefix=ajustes.api_v1_prefix)
app.include_router(usuarios.router, prefix=ajustes.api_v1_prefix)
app.include_router(combustibles.router, prefix=ajustes.api_v1_prefix)
app.include_router(configuracion.router, prefix=ajustes.api_v1_prefix)
app.include_router(instituciones.router, prefix=ajustes.api_v1_prefix)
app.include_router(ordenes.router, prefix=ajustes.api_v1_prefix)
app.include_router(vales.router_emision, prefix=ajustes.api_v1_prefix)
app.include_router(vales.router_vales, prefix=ajustes.api_v1_prefix)
registrar_manejadores(app)

"""Punto de entrada de la API (`fastapi dev`)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import obtener_settings
from app.db.sesion import motor
from app.routers import sistema

ajustes = obtener_settings()


@asynccontextmanager
async def ciclo_vida(_: FastAPI) -> AsyncIterator[None]:
    """Cierra el pool de conexiones al apagar la aplicación."""
    yield
    await motor.dispose()


app = FastAPI(
    title="San José API",
    description="Gestión de vales de combustible de la estación de servicio San José.",
    version="0.1.0",
    lifespan=ciclo_vida,
)

app.include_router(sistema.router, prefix=ajustes.api_v1_prefix)

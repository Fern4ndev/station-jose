"""Motor y sesiones de SQLAlchemy sobre PostgreSQL."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import obtener_settings

ajustes = obtener_settings()

motor = create_async_engine(
    ajustes.database_url,
    # Valor por defecto de PostgreSQL, declarado de forma explícita (plan, sección 1).
    isolation_level="READ COMMITTED",
    pool_pre_ping=True,
)

FabricaSesiones = async_sessionmaker(motor, expire_on_commit=False)


async def obtener_sesion() -> AsyncIterator[AsyncSession]:
    """Entrega una sesión por petición y la cierra al terminar."""
    async with FabricaSesiones() as sesion:
        yield sesion


SesionBd = Annotated[AsyncSession, Depends(obtener_sesion)]

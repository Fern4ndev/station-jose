"""Catálogos cerrados para el frontend (plan, sección 5.1).

En la Fase 2 llegará la autenticación; entonces este endpoint declarará el
permiso `sesion`. Mientras tanto responde porque el frontend necesita las
listas para construir formularios desde la primera pantalla.
"""

from fastapi import APIRouter

from app.core import dominio
from app.schemas.sistema import EnumsRespuesta

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/enums")
async def enums() -> EnumsRespuesta:
    """Listas cerradas de estados, tipos, emisores, roles y permisos."""
    return EnumsRespuesta(
        roles=list(dominio.ROLES),
        permisos=list(dominio.PERMISOS),
        tipos_institucion=list(dominio.TIPOS_INSTITUCION),
        estados_institucion=list(dominio.ESTADOS_INSTITUCION),
        modalidades_numeracion=list(dominio.MODALIDADES_NUMERACION),
        estados_orden=list(dominio.ESTADOS_ORDEN),
        estados_ocr=list(dominio.ESTADOS_OCR),
        metodos_ocr=list(dominio.METODOS_OCR),
        emisores_vale=list(dominio.EMISORES_VALE),
        estados_vale=list(dominio.ESTADOS_VALE),
        tipos_movimiento=list(dominio.TIPOS_MOVIMIENTO),
    )

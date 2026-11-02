"""Catálogos cerrados para el frontend (plan, sección 5.1).

Requieren una sesión válida (AUT-09): cualquier usuario autenticado puede
leerlos porque alimentan formularios y menús. Con `must_change_password`
en TRUE la dependencia común los bloquea hasta el cambio (AUT-06); para el
resto de permisos entra `requiere_permiso` en la Fase 3.
"""

from fastapi import APIRouter

from app.core import dominio
from app.dependencies import UsuarioActual
from app.schemas.sistema import EnumsRespuesta

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/enums")
async def enums(_: UsuarioActual) -> EnumsRespuesta:
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

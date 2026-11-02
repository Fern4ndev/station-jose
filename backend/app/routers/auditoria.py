"""Módulo Auditoría e integridad (M11, plan sección 5.13, Fase 8).

La bitácora (AUD-03) es de solo lectura y queda bajo `auditoria.ver`, que solo
tiene el administrador; el historial por registro (AUD-04) lo comparten
administrador y oficina con `historial.ver`. La verificación de saldos
(AUD-05) corre a demanda desde aquí o con `python -m app.cli verificar-saldos`,
y la revisión de una diferencia (AUD-06) deja su propio rastro en la bitácora.
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.errors import ErrorDominio
from app.schemas.auditoria import (
    Bitacora,
    DiferenciaFila,
    Diferencias,
    Historial,
    RevisionEntrada,
    UltimaVerificacion,
    Verificaciones,
    VerificacionFila,
)
from app.services import auditoria as servicio_bitacora
from app.services import integridad as servicio_integridad

router = APIRouter(prefix="/auditoria", tags=["auditoria"])

# AUD-04: entidades con historial navegable (plan, sección 5.13).
EntidadHistorial = Literal["orden", "vale", "institucion", "usuario", "combustible"]


def _auditoria() -> object:
    return requiere_permiso("auditoria.ver")


def _historial() -> object:
    return requiere_permiso("historial.ver")


@router.get("/bitacora", response_model=Bitacora)
async def bitacora(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
    usuario_id: Annotated[int | None, Query(ge=1)] = None,
    accion: Annotated[str | None, Query(max_length=60)] = None,
    entidad: Annotated[str | None, Query(max_length=60)] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Bitacora:
    """AUD-03: acciones registradas, con filtros y paginación."""
    if desde is not None and hasta is not None and desde > hasta:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"desde": ["La fecha inicial no puede ser posterior a la final."]},
        )
    items, total = await servicio_bitacora.listar_bitacora(
        sesion,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return Bitacora(
        items=items, total=total, pagina=pagina, por_pagina=por_pagina
    )


@router.get("/historial/{entidad}/{entidad_id}", response_model=Historial)
async def historial(
    entidad: EntidadHistorial,
    entidad_id: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_historial()),  # noqa: B008
) -> Historial:
    """AUD-04: todo lo que le pasó a una orden, vale, institución, usuario o
    combustible, de lo más reciente a lo más antiguo.
    """
    items = await servicio_bitacora.historial(
        sesion, entidad=entidad, entidad_id=entidad_id
    )
    return Historial(entidad=entidad, entidad_id=entidad_id, items=items)


@router.get("/integridad/ultima", response_model=UltimaVerificacion)
async def ultima_verificacion(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
) -> UltimaVerificacion:
    """AUD-05: resultado de la última verificación y alertas pendientes."""
    return UltimaVerificacion(
        verificacion=await servicio_integridad.ultima(sesion),
        diferencias_pendientes=await servicio_integridad.pendientes(sesion),
    )


@router.get("/integridad/verificaciones", response_model=Verificaciones)
async def verificaciones(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Verificaciones:
    """AUD-05: historial de corridas, la más reciente primero."""
    items, total = await servicio_integridad.verificaciones(
        sesion, pagina=pagina, por_pagina=por_pagina
    )
    return Verificaciones(
        items=items, total=total, pagina=pagina, por_pagina=por_pagina
    )


@router.post("/integridad/verificar", response_model=VerificacionFila)
async def verificar(
    request: Request,
    sesion: SesionBd,
    administrador: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
) -> VerificacionFila:
    """AUD-05: compara todos los saldos con sus movimientos en este momento."""
    resultado = await servicio_integridad.verificar(
        sesion,
        actor_id=administrador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return VerificacionFila(**resultado)


@router.get("/integridad/diferencias", response_model=Diferencias)
async def diferencias(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
    revisada: Annotated[bool | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Diferencias:
    """AUD-06: descuadres detectados; `revisada=false` deja los pendientes."""
    items, total = await servicio_integridad.listar_diferencias(
        sesion, revisada=revisada, pagina=pagina, por_pagina=por_pagina
    )
    return Diferencias(
        items=items, total=total, pagina=pagina, por_pagina=por_pagina
    )


@router.post(
    "/integridad/diferencias/{diferencia_id}/revisar", response_model=DiferenciaFila
)
async def revisar_diferencia(
    diferencia_id: int,
    peticion: RevisionEntrada,
    request: Request,
    sesion: SesionBd,
    administrador: UsuarioAutenticado = Depends(_auditoria()),  # noqa: B008
) -> DiferenciaFila:
    """AUD-06: cierra la diferencia con el comentario del administrador."""
    revisada = await servicio_integridad.revisar(
        sesion,
        diferencia_id,
        comentario=peticion.comentario,
        actor_id=administrador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return DiferenciaFila(**revisada)

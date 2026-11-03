"""Endpoints de lectura de saldos y consumos (Fase 12)."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.db.sesion import SesionBd
from app.dependencies import UsuarioAutenticado, requiere_permiso
from app.errors import ErrorDominio
from app.services import consultas as servicio

router = APIRouter(prefix="/consultas", tags=["consultas"])
UsuarioConsultas = Annotated[UsuarioAutenticado, Depends(requiere_permiso("consultas.ver"))]


@router.get("/saldo/ordenes/{orden_id}")
async def saldo_orden(orden_id: int, sesion: SesionBd, _: UsuarioConsultas) -> dict:
    return await servicio.saldo_orden(sesion, orden_id)


@router.get("/saldo/instituciones/{institucion_id}")
async def saldo_institucion(institucion_id: int, sesion: SesionBd, _: UsuarioConsultas) -> dict:
    return await servicio.saldo_institucion(sesion, institucion_id)


@router.get("/consumo")
async def consumo(
    sesion: SesionBd,
    _: UsuarioConsultas,
    institucion_id: Annotated[int | None, Query(ge=1)] = None,
    orden_id: Annotated[int | None, Query(ge=1)] = None,
    vale_id: Annotated[int | None, Query(ge=1)] = None,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: Literal["dia", "semana", "mes"] = "dia",
    combustible_id: Annotated[int | None, Query(ge=1)] = None,
    estado: str | None = None,
    emisor: Literal["estacion", "entidad"] | None = None,
) -> list[dict]:
    if desde and hasta and desde > hasta:
        raise ErrorDominio(422, "VALIDACION_INVALIDA", "desde no puede ser posterior a hasta.")
    return await servicio.consumo(
        sesion,
        institucion_id=institucion_id,
        orden_id=orden_id,
        vale_id=vale_id,
        combustible_id=combustible_id,
        estado=estado,
        emisor=emisor,
        desde=desde,
        hasta=hasta,
        agrupacion=agrupacion,
    )


@router.get("/estado-cuenta/{institucion_id}")
async def estado_cuenta(
    institucion_id: int,
    sesion: SesionBd,
    _: UsuarioConsultas,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    if desde and hasta and desde > hasta:
        raise ErrorDominio(422, "VALIDACION_INVALIDA", "desde no puede ser posterior a hasta.")
    return await servicio.estado_cuenta(sesion, institucion_id, desde=desde, hasta=hasta)

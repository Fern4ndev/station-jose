"""Endpooints del módulo Consumos (plan sección 5.10, Fase 7).

El despacho y el comprobante quedan bajo `consumos.registrar` (oficina y
despachador lo tienen) y la reversión bajo `consumos.revertir` (solo el
administrador). La transacción es del servicio: el router solo valida,
llama y confirma al final.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.schemas.consumos import (
    Comprobante,
    ConsumoEntrada,
    ConsumoRevertir,
    MovimientoSalida,
)
from app.services import consumos as servicio

router = APIRouter(tags=["consumos"])


def _registrar() -> object:
    return requiere_permiso("consumos.registrar")


def _ver() -> object:
    return requiere_permiso("vales.ver")


def _revertir() -> object:
    return requiere_permiso("consumos.revertir")


def _fecha_o_nada(valor: str | None) -> str | None:
    """La fecha opcional validada por el esquema pasa tal cual."""
    return valor if valor else None


@router.post(
    "/vales/{vale_id}/consumos", response_model=MovimientoSalida, status_code=201
)
async def registrar_consumo(
    vale_id: int,
    peticion: ConsumoEntrada,
    request: Request,
    sesion: SesionBd,
    operador: UsuarioAutenticado = Depends(_registrar()),  # noqa: B008
) -> MovimientoSalida:
    """CON-01..09: despacha sobre el vale; el token evita el doble envío."""
    movimiento, _ = await servicio.registrar_consumo(
        sesion,
        vale_id,
        token_operacion=str(peticion.token_operacion),
        cantidad_galones=peticion.cantidad_galones,
        importe_soles=peticion.importe_soles,
        combustible_id=peticion.combustible_id,
        placa=peticion.placa,
        conductor=peticion.conductor,
        observacion=peticion.observacion,
        fecha_local=_fecha_o_nada(peticion.fecha_local),
        motivo=peticion.motivo,
        actor=operador,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return MovimientoSalida(**movimiento)


@router.get("/vales/{vale_id}/consumos", response_model=list[dict])
async def listar_consumos(
    vale_id: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
    desde: Annotated[str | None, Query(max_length=10)] = None,
    hasta: Annotated[str | None, Query(max_length=10)] = None,
) -> list[dict]:
    """QRY-05: consumos del vale en el rango pedido, reversiones incluidas."""
    filas = await servicio.listar_consumos(
        sesion, vale_id, desde=desde, hasta=hasta
    )
    await sesion.commit()
    return filas


@router.post("/consumos/{movimiento_id}/revertir", response_model=dict)
async def revertir(
    movimiento_id: int,
    peticion: ConsumoRevertir,
    request: Request,
    sesion: SesionBd,
    administrador: UsuarioAutenticado = Depends(_revertir()),  # noqa: B008
) -> dict:
    """CON-11: movimiento inverso del consumo; uno solo por movimiento."""
    reversion = await servicio.revertir(
        sesion,
        movimiento_id,
        motivo=peticion.motivo,
        actor=administrador,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return reversion


@router.get("/consumos/{movimiento_id}/comprobante", response_model=Comprobante)
async def comprobante(
    movimiento_id: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_registrar()),  # noqa: B008
) -> Comprobante:
    """CON-10: los datos para el comprobante imprimible."""
    ficha = await servicio.comprobante(sesion, movimiento_id)
    await sesion.commit()
    return Comprobante(**ficha)

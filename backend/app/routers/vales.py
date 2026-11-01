"""Módulo Vales, Fase 6 (M07, plan sección 5.9).

Emisión de vales de estación y registro de vales de entidad con
`vales.emitir`; lectura del módulo con `vales.ver`. La anulación, los
ajustes y el procesamiento de vencimientos son de la Fase 7. La emisión es
atómica (VAL-04): el router confirma la transacción al final y el servicio
levanta `ErrorDominio` antes de escribir si algo no cuadra.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core import dinero
from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.schemas.vales import (
    AlertasSalida,
    ImpresionSalida,
    SimulacionEntrada,
    SimulacionSalida,
    ValeDetalle,
    ValeEmitido,
    ValeEntidadEntrada,
    ValeEstacionEntrada,
    ValeRow,
    ValesLista,
)
from app.services import vales as servicio

router_emision = APIRouter(prefix="/ordenes", tags=["vales"])
router_vales = APIRouter(prefix="/vales", tags=["vales"])


def _ver() -> object:
    return requiere_permiso("vales.ver")


def _emitir() -> object:
    return requiere_permiso("vales.emitir")


def _fecha_o_nada(valor: str | None) -> date | None:
    """Traduce la fecha opcional validada por el esquema."""
    if valor is None:
        return None
    return date.fromisoformat(valor)


# -----------------------------------------------------------------------
# Emisión sobre la orden (VAL-01..05, CMB-04)
# -----------------------------------------------------------------------


@router_emision.post("/{orden_id}/vales/simulacion", response_model=SimulacionSalida)
async def simular(
    orden_id: int,
    peticion: SimulacionEntrada,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_emitir()),  # noqa: B008
) -> SimulacionSalida:
    """VAL-01/VAL-03: vista previa de la emisión; no guarda nada."""
    datos = await servicio.simulacion(
        sesion,
        orden_id,
        combustible_id=peticion.combustible_id,
        cantidades=peticion.cantidades,
    )
    await sesion.commit()  # Solo lectura; cierra la transacción igual.
    return SimulacionSalida(**datos)


@router_emision.post(
    "/{orden_id}/vales", response_model=list[ValeEmitido], status_code=201
)
async def emitir(
    orden_id: int,
    peticion: ValeEstacionEntrada,
    request: Request,
    sesion: SesionBd,
    emisor: UsuarioAutenticado = Depends(_emitir()),  # noqa: B008
) -> list[ValeEmitido]:
    """VAL-01..04: emisión atómica de vales de estación; todos o ninguno."""
    emitidos = await servicio.emitir_estacion(
        sesion,
        orden_id,
        combustible_id=peticion.combustible_id,
        cantidades=peticion.cantidades,
        fecha_vencimiento=_fecha_o_nada(peticion.fecha_vencimiento),
        actor_id=emisor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return [ValeEmitido(**vale) for vale in emitidos]


@router_emision.post(
    "/{orden_id}/vales-entidad", response_model=ValeEmitido, status_code=201
)
async def registrar_entidad(
    orden_id: int,
    peticion: ValeEntidadEntrada,
    request: Request,
    sesion: SesionBd,
    emisor: UsuarioAutenticado = Depends(_emitir()),  # noqa: B008
) -> ValeEmitido:
    """VAL-05/VAL-15: registro del vale emitido por la propia institución."""
    vale = await servicio.registrar_entidad(
        sesion,
        orden_id,
        numero_entidad=peticion.numero_entidad,
        combustible_id=peticion.combustible_id,
        cantidad=dinero.monto(peticion.cantidad),
        fecha_vencimiento=_fecha_o_nada(peticion.fecha_vencimiento),
        actor_id=emisor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return ValeEmitido(
        id=vale["id"],
        numero_estacion=None,
        numero_entidad=vale["numero_entidad"],
        cantidad_inicial=vale["cantidad_inicial"],
        saldo=vale["saldo"],
        valor_soles=vale["valor_soles"],
        precio_galon_aplicado=vale["precio_galon_aplicado"],
        emisor=vale["emisor"],
        estado=vale["estado"],
    )


# -----------------------------------------------------------------------
# Consultas del módulo (VAL-06..08, QRY-01, VAL-12)
# -----------------------------------------------------------------------


@router_vales.get("", response_model=ValesLista)
async def listar(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
    q: Annotated[str | None, Query(max_length=80)] = None,
    institucion_id: Annotated[int | None, Query()] = None,
    orden_id: Annotated[int | None, Query()] = None,
    estado: Annotated[str | None, Query(max_length=20)] = None,
    combustible_id: Annotated[int | None, Query()] = None,
    emisor: Annotated[str | None, Query(max_length=20)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ValesLista:
    """VAL-06: listado paginado con búsqueda por número y filtros."""
    items, total = await servicio.listar(
        sesion,
        q=q,
        institucion_id=institucion_id,
        orden_id=orden_id,
        estado=estado,
        combustible_id=combustible_id,
        emisor=emisor,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    await sesion.commit()
    return ValesLista(
        items=[ValeRow(**fila) for fila in items],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router_vales.get("/buscar", response_model=list[ValeRow])
async def buscar(
    sesion: SesionBd,
    q: Annotated[str, Query(min_length=1, max_length=80)],
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> list[ValeRow]:
    """QRY-01: hasta 8 candidatos con institución, orden, combustible y saldo."""
    candidato = await servicio.buscar(sesion, q)
    await sesion.commit()
    return [ValeRow(**fila) for fila in candidato]


@router_vales.get("/alertas", response_model=AlertasSalida)
async def alertas(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> AlertasSalida:
    """VAL-13: franja de alertas (saldo bajo y por vencer)."""
    datos = await servicio.alertas(sesion)
    await sesion.commit()
    return AlertasSalida(**datos)


@router_vales.get("/{id_vale}", response_model=ValeDetalle)
async def detalle(
    id_vale: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> ValeDetalle:
    """VAL-07/VAL-08: ficha completa; un vencido se reconoce al consultar."""
    ficha = await servicio.detalle(sesion, id_vale)
    await sesion.commit()
    return ValeDetalle(**ficha)


@router_vales.get("/{id_vale}/movimientos", response_model=list[dict])
async def movimientos(
    id_vale: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> list[dict]:
    """CON-12: línea de tiempo del vale."""
    historia = await servicio.movimientos(sesion, id_vale)
    await sesion.commit()
    return historia


@router_vales.post("/{id_vale}/impresion", response_model=ImpresionSalida)
async def registrar_impresion(
    id_vale: int,
    request: Request,
    sesion: SesionBd,
    emisor: UsuarioAutenticado = Depends(_emitir()),  # noqa: B008
) -> ImpresionSalida:
    """VAL-12: registra la impresión; desde la segunda marca duplicado."""
    ficha = await servicio.registrar_impresion(
        sesion,
        id_vale,
        actor_id=emisor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return ImpresionSalida(
        id=int(ficha["id"]),
        emisor=str(ficha["emisor"]),
        numero_estacion=ficha.get("numero_estacion"),
        numero_entidad=ficha.get("numero_entidad"),
        estado=str(ficha["estado"]),
        veces_impreso=int(ficha["veces_impreso"]),
        es_duplicado=bool(ficha["es_duplicado"]),
    )

"""Catálogo de combustibles y precios (M04, plan sección 5.5).

Lectura con `catalogo.ver`; cambios con `catalogo.gestionar`. Los precios
solo admiten registrar: nunca hay edición ni borrado (CMB-02/RN-16).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.schemas.combustibles import (
    CombustibleCrear,
    CombustibleEditar,
    CombustibleSalida,
    CombustiblesLista,
    PrecioEntrada,
    PrecioRegistrado,
)
from app.services import combustibles as servicio
from app.services import precios

router = APIRouter(prefix="/combustibles", tags=["combustibles"])


def _ver() -> Callable:
    return requiere_permiso("catalogo.ver")


def _gestionar() -> Callable:
    return requiere_permiso("catalogo.gestionar")


def _salida(fila: dict) -> CombustibleSalida:
    """Traduce la fila del catálogo al esquema con el precio vigente."""
    return CombustibleSalida(
        id=int(fila["id"]),
        nombre=str(fila["nombre"]),
        activo=fila["activo"],
        creado_en=fila["creado_en"],
        precio_vigente=fila.get("precio_vigente"),
    )


@router.get("", response_model=CombustiblesLista)
async def listar(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
    activo: Annotated[bool | None, Query()] = None,
) -> CombustiblesLista:
    """CMB-01/03: tipos con el precio vigente de cada uno; filtro opcional."""
    items = await servicio.listar(sesion, activo=activo)
    return CombustiblesLista(items=[_salida(fila) for fila in items])


@router.post("", response_model=CombustibleSalida, status_code=201)
async def crear(
    peticion: CombustibleCrear,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> CombustibleSalida:
    """CMB-01: alta del tipo; el nombre no se repite."""
    fila = await servicio.crear(
        sesion,
        nombre=peticion.nombre,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _salida(fila)


@router.patch("/{combustible_id}", response_model=CombustibleSalida)
async def editar(
    combustible_id: int,
    peticion: CombustibleEditar,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> CombustibleSalida:
    """CMB-01: cambia nombre o activo; no existe borrado físico."""
    fila = await servicio.editar(
        sesion,
        combustible_id,
        nombre=peticion.nombre,
        activo=peticion.activo,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _salida(fila)


@router.get("/{combustible_id}/precios", response_model=list)
async def historico_precios(
    combustible_id: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> list[dict]:
    """CMB-03: histórico del más reciente al más antiguo, con quién lo registró."""
    await servicio.obtener(sesion, combustible_id)  # 404 si el tipo no existe.
    return await precios.historico(sesion, combustible_id)


@router.post("/{combustible_id}/precios", response_model=PrecioRegistrado, status_code=201)
async def registrar_precio(
    combustible_id: int,
    peticion: PrecioEntrada,
    request: Request,
    sesion: SesionBd,
    gestionador: UsuarioAutenticado = Depends(_gestionar()),  # noqa: B008
) -> PrecioRegistrado:
    """CMB-02: registra un precio nuevo; la fecha no retrocede y las filas son inmutables."""
    fila = await precios.registrar(
        sesion,
        combustible_id=combustible_id,
        precio_galon=peticion.precio_galon,
        vigente_desde=peticion.vigente_desde,
        actor_id=gestionador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return PrecioRegistrado(
        id=int(fila["id"]),
        combustible_id=int(fila["combustible_id"]),
        precio_galon=str(fila["precio_galon"]),
        vigente_desde=str(fila["vigente_desde"]),
        creado_en=fila["creado_en"],
    )

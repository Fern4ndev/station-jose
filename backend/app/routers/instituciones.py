"""Módulo Instituciones (M03, plan sección 5.6).

Lectura con `instituciones.ver`; alta y edición con `instituciones.editar`;
desactivar/reactivar solo con `instituciones.desactivar` (INS-06/07). El
cambio obligatorio de contraseña lo intercepta la dependencia común antes
de llegar aquí.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.schemas.instituciones import (
    InstitucionDetalle,
    InstitucionEditar,
    InstitucionEntrada,
    InstitucionesLista,
    InstitucionSalida,
    RespuestaInactivada,
    VerificacionRuc,
)
from app.services import instituciones as servicio

router = APIRouter(prefix="/instituciones", tags=["instituciones"])


def _ver() -> Callable:
    return requiere_permiso("instituciones.ver")


def _editar() -> Callable:
    return requiere_permiso("instituciones.editar")


def _desactivar() -> Callable:
    return requiere_permiso("instituciones.desactivar")


def _salida(fila: dict) -> InstitucionSalida:
    return InstitucionSalida(
        id=int(fila["id"]),
        nombre=str(fila["nombre"]),
        ruc=str(fila["ruc"]),
        tipo=str(fila["tipo"]),
        modalidad_numeracion=str(fila["modalidad_numeracion"]),
        estado=str(fila["estado"]),
        creado_en=fila["creado_en"],
        actualizado_en=fila["actualizado_en"],
    )


def _detalle(fila: dict) -> InstitucionDetalle:
    return InstitucionDetalle(
        id=int(fila["id"]),
        nombre=str(fila["nombre"]),
        ruc=str(fila["ruc"]),
        direccion=fila["direccion"],
        telefono=fila["telefono"],
        correo=fila["correo"],
        representante=fila["representante"],
        tipo=str(fila["tipo"]),
        modalidad_numeracion=str(fila["modalidad_numeracion"]),
        estado=str(fila["estado"]),
        creado_en=fila["creado_en"],
        actualizado_en=fila["actualizado_en"],
        ordenes=int(fila["ordenes"]),
        presupuesto_total=str(fila["presupuesto_total"]),
        vales_vigentes=int(fila["vales_vigentes"]),
        saldo_vigente_soles=str(fila["saldo_vigente_soles"]),
        consumo_mes_soles=str(fila["consumo_mes_soles"]),
    )


@router.get("", response_model=InstitucionesLista)
async def listar(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
    texto: Annotated[str | None, Query(max_length=120)] = None,
    ruc: Annotated[str | None, Query(pattern=r"^[0-9]{11}$")] = None,
    tipo: Annotated[str | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InstitucionesLista:
    """INS-03: listado paginado con texto, RUC exacto, tipo y estado."""
    items, total = await servicio.listar(
        sesion,
        texto=texto,
        ruc_valor=ruc,
        tipo=tipo,
        estado=estado,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return InstitucionesLista(
        items=[_salida(fila) for fila in items],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get("/ruc/{ruc}", response_model=VerificacionRuc)
async def verificar_ruc(
    ruc: Annotated[str, Path(max_length=20)],
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> VerificacionRuc:
    """INS-01/OCR-08: validez del RUC y enlace a la existente, para validar
    en vivo antes del alta; trae la institución ya registrada si la hay.
    """
    return VerificacionRuc.model_validate(await servicio.verificar_ruc(sesion, ruc))


@router.post("", response_model=InstitucionDetalle, status_code=201)
async def crear(
    peticion: InstitucionEntrada,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> InstitucionDetalle:
    """INS-01: alta con verificación del dígito verificador del RUC."""
    id_nuevo = await servicio.crear(
        sesion,
        nombre=peticion.nombre,
        ruc_valor=peticion.ruc,
        direccion=peticion.direccion,
        telefono=peticion.telefono,
        correo=peticion.correo,
        representante=peticion.representante,
        tipo=peticion.tipo,
        modalidad_numeracion=peticion.modalidad_numeracion,
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _detalle(await servicio.ficha(sesion, id_nuevo))


@router.get("/{id_institucion}", response_model=InstitucionDetalle)
async def ficha(
    id_institucion: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> InstitucionDetalle:
    """INS-03: ficha completa con los resúmenes de órdenes."""
    return _detalle(await servicio.ficha(sesion, id_institucion))


@router.patch("/{id_institucion}", response_model=InstitucionDetalle)
async def editar(
    id_institucion: int,
    peticion: InstitucionEditar,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> InstitucionDetalle:
    """INS-04: edición parcial; RUC/modalidad con órdenes solo administrador."""
    fila = await servicio.editar(
        sesion,
        id_institucion,
        datos=peticion.model_dump(exclude_unset=True),
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
        es_admin=editor.rol == "administrador",
    )
    await sesion.commit()
    return _detalle(await servicio.ficha(sesion, int(fila["id"])))


@router.post("/{id_institucion}/desactivar", response_model=RespuestaInactivada)
async def desactivar(
    id_institucion: int,
    request: Request,
    sesion: SesionBd,
    desactivador: UsuarioAutenticado = Depends(_desactivar()),  # noqa: B008
) -> RespuestaInactivada:
    """INS-06: baja lógica (estado = 'inactiva'); la fila no se elimina."""
    await servicio.desactivar(
        sesion,
        id_institucion,
        actor_id=desactivador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return RespuestaInactivada(id=id_institucion, estado="inactiva")


@router.post("/{id_institucion}/reactivar", response_model=RespuestaInactivada)
async def reactivar(
    id_institucion: int,
    request: Request,
    sesion: SesionBd,
    reactivador: UsuarioAutenticado = Depends(_desactivar()),  # noqa: B008
) -> RespuestaInactivada:
    """INS-07: reactivación sin perder ni un dato de la fila."""
    await servicio.reactivar(
        sesion,
        id_institucion,
        actor_id=reactivador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return RespuestaInactivada(id=id_institucion, estado="activa")

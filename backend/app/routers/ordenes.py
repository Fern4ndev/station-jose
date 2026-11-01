"""Módulo Órdenes de compra (M03, plan sección 5.7).

Lectura con `ordenes.ver`; alta, edición, adjuntar documento, marcar
vigente y cerrar con `ordenes.editar`; anular solo con `ordenes.anular`
(ORD-09). La advertencia de duplicado (ORD-08) tiene su propio endpoint
`POST /ordenes/duplicado` y el alta la cruza de nuevo antes de guardar.
"""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core import archivos, dinero
from app.db.sesion import SesionBd
from app.dependencies import (
        UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.schemas.ordenes import (
    AnulacionEntrada,
    ArchivoAdjunto,
    OrdenCrear,
    OrdenDetalle,
    OrdenEditar,
    OrdenesLista,
    OrdenEstado,
    OrdenSalida,
    OrdenSerie,
    ValeResumen,
)
from app.services import ordenes as servicio

router = APIRouter(prefix="/ordenes", tags=["ordenes"])


def _ver() -> Callable:
    return requiere_permiso("ordenes.ver")


def _editar() -> Callable:
    return requiere_permiso("ordenes.editar")


def _anular() -> Callable:
    return requiere_permiso("ordenes.anular")


def _salida(fila: dict) -> OrdenSalida:
    return OrdenSalida(
        id=int(fila["id"]),
        institucion_id=int(fila["institucion_id"]),
        razon_social=str(fila["razon_social"]),
        anio=int(fila["anio"]),
        numero=str(fila["numero"]),
        fecha_emision=fila["fecha_emision"],
        presupuesto_soles=str(fila["presupuesto_soles"]),
        estado=str(fila["estado"]),
        combustible_id=fila["combustible_id"],
        creado_en=fila["creado_en"],
    )


def _vale(fila: dict) -> ValeResumen:
    return ValeResumen(
        id=int(fila["id"]),
        emisor=str(fila["emisor"]),
        numero_estacion=fila["numero_estacion"],
        numero_entidad=fila["numero_entidad"],
        estado=str(fila["estado"]),
        saldo=str(fila["saldo"]),
        valor_soles=str(fila["valor_soles"]),
        fecha_emision=fila["fecha_emision"],
    )


def _orden_detalle(fila: dict) -> OrdenDetalle:
    return OrdenDetalle(
        id=int(fila["id"]),
        institucion_id=int(fila["institucion_id"]),
        razon_social=str(fila["razon_social"]),
        institucion_ruc=fila["institucion_ruc"],
        anio=int(fila["anio"]),
        numero=str(fila["numero"]),
        fecha_emision=fila["fecha_emision"],
        presupuesto_soles=str(fila["presupuesto_soles"]),
        observaciones=fila["observaciones"],
        estado=str(fila["estado"]),
        serie_desde=fila["serie_desde"],
        serie_hasta=fila["serie_hasta"],
        combustible_id=fila["combustible_id"],
        archivo_path=fila["archivo_path"],
        archivo_tipo=fila["archivo_tipo"],
        archivo_tamano=fila["archivo_tamano"],
        creado_en=fila["creado_en"],
        actualizado_en=fila["actualizado_en"],
        total_emitido_soles=fila["total_emitido_soles"],
        total_emitido_galones=fila["total_emitido_galones"],
        presupuesto_restante_soles=fila["presupuesto_restante_soles"],
        total_consumido_soles=fila["total_consumido_soles"],
        cantidad_vales=int(fila["cantidad_vales"]),
        vales=[_vale(v) for v in fila["vales"]],
    )


def _detalle(fila: dict) -> OrdenDetalle:
    """Alias que conservan los endpoints nacidos con la Fase 5."""
    return _orden_detalle(fila)


@router.get("", response_model=OrdenesLista)
async def listar(
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
    institucion_id: Annotated[int | None, Query()] = None,
    estado: Annotated[str | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    texto: Annotated[str | None, Query(max_length=120)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OrdenesLista:
    """ORD-05: listado paginado con filtros de institución, estado y fechas."""
    items, total = await servicio.listar(
        sesion,
        institucion_id=institucion_id,
        estado=estado,
        desde=desde,
        hasta=hasta,
        texto=texto,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return OrdenesLista(
        items=[_salida(fila) for fila in items],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.post("/duplicado", response_model=dict)
async def advertencia_duplicado(
    peticion: OrdenCrear,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> dict:
    """ORD-08: cruza la orden nueva contra la institución antes de guardar.

    Devuelve `{certificada: true}` cuando hay coincidencia exacta de
    institución, presupuesto y fecha; el cliente pide confirmación al
    usuario y reenvía el alta con `confirmar_duplicado = TRUE`.
    """
    duplicado = await servicio.posible_duplicado(
        sesion,
        institucion_id=peticion.institucion_id,
        presupuesto_soles=dinero.monto(peticion.presupuesto_soles),
        fecha_emision=date.fromisoformat(peticion.fecha_emision),
    )
    if duplicado is None:
        return {"certificada": False, "orden": None}
    return {"certificada": True, "orden": _salida(duplicado).model_dump(mode="json")}


@router.post("", response_model=OrdenDetalle, status_code=201)
async def crear(
    peticion: OrdenCrear,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> OrdenDetalle:
    """ORD-01/02: alta con institución activa, presupuesto > 0 y número
    único por institución y año (RN-01, RN-12). Si el cheque de duplicado se
    activa, la petición debe traer `confirmar_duplicado = TRUE`.
    """
    id_orden = await servicio.crear(
        sesion,
        institucion_id=peticion.institucion_id,
        numero=peticion.numero,
        fecha_emision=date.fromisoformat(peticion.fecha_emision),
        presupuesto_soles=dinero.monto(peticion.presupuesto_soles),
        observaciones=peticion.observaciones,
        combustible_id=peticion.combustible_id,
        serie_desde=peticion.serie_desde,
        serie_hasta=peticion.serie_hasta,
        estado_inicial=peticion.estado,
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
        confirmar_duplicado=peticion.confirmar_duplicado,
    )
    await sesion.commit()
    return _detalle(await servicio.obtener(sesion, id_orden))


@router.get("/{id_orden}", response_model=OrdenDetalle)
async def obtener(
    id_orden: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> OrdenDetalle:
    """ORD-06: ficha completa con totales derivados de sus vales (RN-03)."""
    return _detalle(await servicio.obtener(sesion, id_orden))


@router.patch("/{id_orden}", response_model=OrdenDetalle)
async def editar(
    id_orden: int,
    peticion: OrdenEditar,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> OrdenDetalle:
    """ORD-03: edición parcial; solo borrador/vigente y con vales solo observaciones."""
    fila = await servicio.editar(
        sesion,
        id_orden,
        datos=peticion.model_dump(exclude_unset=True),
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return _detalle(await servicio.obtener(sesion, int(fila["id"])))


@router.post("/{id_orden}/archivo", response_model=ArchivoAdjunto)
async def adjuntar_archivo(
    id_orden: int,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> ArchivoAdjunto:
    """ORD-04: sube el documento (PDF/JPG/PNG por firma binaria); reemplaza el anterior."""
    contenido = await request.body()
    resultado = await servicio.adjuntar_archivo(
        sesion,
        id_orden,
        datos_archivo=contenido,
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    orden = await servicio.obtener(sesion, id_orden)
    tamano = int(orden["archivo_tamano"] or 0)
    hash_archivo = str(orden["archivo_hash"] or "")
    return ArchivoAdjunto(
        archivo_path=resultado["archivo_path"],
        media_type=resultado["media_type"],
        archivo_tamano=tamano,
        archivo_hash=hash_archivo,
    )


@router.get("/{id_orden}/archivo")
async def leer_archivo(
    id_orden: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> StreamingResponse:
    """ORD-04: descarga en bloques con hash fijo; `inline` y `nosniff` listos."""
    media_type, path, tamano, hash_esperado = await servicio.leer_archivo(sesion, id_orden)
    await sesion.commit()  # La lectura no muda datos; cierra la transacción igual.
    if not tamano:
        tamano = 0
    cabeceras = {
        "Content-Disposition": f'inline; filename="orden-{id_orden}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Length": str(tamano),
    }
    if not hash_esperado:
        hash_esperado = "0" * 64
    return StreamingResponse(
        archivos.leer_bloques(path, hash_esperado),
        media_type=media_type,
        headers=cabeceras,
    )


@router.post("/{id_orden}/marcar-vigente", response_model=OrdenEstado)
async def marcar_vigente(
    id_orden: int,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> OrdenEstado:
    """ORD-07: borrador → vigente; a partir de aquí la orden emite vales."""
    fila = await servicio.marcar_vigente(
        sesion,
        id_orden,
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return OrdenEstado(id=id_orden, estado=str(fila["estado"]))


@router.post("/{id_orden}/cerrar", response_model=OrdenEstado)
async def cerrar(
    id_orden: int,
    request: Request,
    sesion: SesionBd,
    editor: UsuarioAutenticado = Depends(_editar()),  # noqa: B008
) -> OrdenEstado:
    """ORD-10: vigente → cerrada; ya no admite nuevos vales."""
    fila = await servicio.cerrar(
        sesion,
        id_orden,
        actor_id=editor.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return OrdenEstado(id=id_orden, estado=str(fila["estado"]))


@router.post("/{id_orden}/anular", response_model=OrdenEstado)
async def anular(
    id_orden: int,
    peticion: AnulacionEntrada,
    request: Request,
    sesion: SesionBd,
    anulador: UsuarioAutenticado = Depends(_anular()),  # noqa: B008
) -> OrdenEstado:
    """ORD-09/RN-17: invalidación con motivo obligatorio; jamás si tiene consumos."""
    fila = await servicio.anular(
        sesion,
        id_orden,
        motivo=peticion.motivo,
        actor_id=anulador.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return OrdenEstado(
        id=id_orden,
        estado=str(fila["estado"]),
        motivo_anulacion=fila["motivo_anulacion"],
    )


@router.get("/{id_orden}/serie", response_model=OrdenSerie)
async def serie(
    id_orden: int,
    sesion: SesionBd,
    _: UsuarioAutenticado = Depends(_ver()),  # noqa: B008
) -> OrdenSerie:
    """ORD-02b/VAL-15: stock de la serie (números usados y disponibles)."""
    return OrdenSerie.model_validate(await servicio.serie(sesion, id_orden))

"""API de reportes y exportación XLSX (Fase 12)."""

from datetime import date
from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.db.sesion import SesionBd
from app.dependencies import UsuarioAutenticado, requiere_permiso
from app.errors import ErrorDominio
from app.services import consultas, reportes, xlsx

router = APIRouter(prefix="/reportes", tags=["reportes"])
UsuarioReportes = Annotated[UsuarioAutenticado, Depends(requiere_permiso("reportes.ver"))]
Agrupacion = Literal["dia", "semana", "mes"]


def _rango_valido(desde: date | None, hasta: date | None) -> None:
    if desde and hasta and desde > hasta:
        raise ErrorDominio(422, "VALIDACION_INVALIDA", "desde no puede ser posterior a hasta.")


@router.get("/rangos")
async def rangos(_: UsuarioReportes) -> dict:
    return reportes.rangos()


@router.get("/consumo/periodo")
async def consumo_periodo(
    sesion: SesionBd,
    _: UsuarioReportes,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: Agrupacion = "dia",
    institucion_id: int | None = None,
    orden_id: int | None = None,
    vale_id: int | None = None,
    combustible_id: int | None = None,
    estado: str | None = None,
    emisor: Literal["estacion", "entidad"] | None = None,
) -> list[dict]:
    _rango_valido(desde, hasta)
    return await reportes.consumo_periodo(
        sesion,
        desde=desde,
        hasta=hasta,
        agrupacion=agrupacion,
        institucion_id=institucion_id,
        orden_id=orden_id,
        vale_id=vale_id,
        combustible_id=combustible_id,
        estado=estado,
        emisor=emisor,
    )


@router.get("/consumo/instituciones")
async def consumo_instituciones(
    sesion: SesionBd,
    _: UsuarioReportes,
    desde: date | None = None,
    hasta: date | None = None,
    combustible_id: int | None = None,
) -> list[dict]:
    _rango_valido(desde, hasta)
    return await reportes.consumo_instituciones(
        sesion, desde=desde, hasta=hasta, combustible_id=combustible_id
    )


@router.get("/consumo/combustibles")
async def consumo_combustibles(
    sesion: SesionBd,
    _: UsuarioReportes,
    desde: date | None = None,
    hasta: date | None = None,
    institucion_id: int | None = None,
) -> list[dict]:
    _rango_valido(desde, hasta)
    return await reportes.consumo_combustibles(
        sesion, desde=desde, hasta=hasta, institucion_id=institucion_id
    )


@router.get("/ordenes")
async def ordenes(
    sesion: SesionBd,
    _: UsuarioReportes,
    desde: date | None = None,
    hasta: date | None = None,
    institucion_id: int | None = None,
) -> dict:
    _rango_valido(desde, hasta)
    return await reportes.ordenes_periodo(
        sesion, desde=desde, hasta=hasta, institucion_id=institucion_id
    )


@router.get("/exportar/{reporte}.xlsx")
async def exportar(
    reporte: Literal[
        "consumo-periodo",
        "consumo-instituciones",
        "consumo-combustibles",
        "ordenes",
        "consumo",
        "estado-cuenta",
    ],
    sesion: SesionBd,
    _: UsuarioReportes,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: Agrupacion = "dia",
    institucion_id: int | None = None,
    orden_id: int | None = None,
    vale_id: int | None = None,
    combustible_id: int | None = None,
    estado: str | None = None,
    emisor: Literal["estacion", "entidad"] | None = None,
) -> StreamingResponse:
    _rango_valido(desde, hasta)
    if reporte in ("consumo-periodo", "consumo"):
        filas = await reportes.consumo_periodo(
            sesion,
            desde=desde,
            hasta=hasta,
            agrupacion=agrupacion,
            institucion_id=institucion_id,
            orden_id=orden_id,
            vale_id=vale_id,
            combustible_id=combustible_id,
            estado=estado,
            emisor=emisor,
        )
    elif reporte == "consumo-instituciones":
        filas = await reportes.consumo_instituciones(
            sesion, desde=desde, hasta=hasta, combustible_id=combustible_id
        )
    elif reporte == "consumo-combustibles":
        filas = await reportes.consumo_combustibles(
            sesion, desde=desde, hasta=hasta, institucion_id=institucion_id
        )
    elif reporte == "ordenes":
        agregado = await reportes.ordenes_periodo(
            sesion, desde=desde, hasta=hasta, institucion_id=institucion_id
        )
        filas = [
            {
                "institucion_id": None,
                "institucion": "TOTAL",
                "cantidad_ordenes": agregado["total_ordenes"],
                "presupuesto_soles": agregado["presupuesto_total_soles"],
            },
            *agregado["instituciones"],
        ]
    elif reporte == "estado-cuenta":
        if institucion_id is None:
            raise ErrorDominio(422, "VALIDACION_INVALIDA", "estado-cuenta requiere institucion_id.")
        estado_cuenta = await consultas.estado_cuenta(
            sesion, institucion_id, desde=desde, hasta=hasta
        )
        filas = [
            {
                "id": None,
                "fecha_local": None,
                "tipo": "SALDO INICIAL",
                "vale_id": None,
                "numero_entidad": None,
                "numero_estacion": None,
                "orden_numero": None,
                "variacion": estado_cuenta["saldo_inicial"],
                "saldo_posterior": None,
            },
            *estado_cuenta["movimientos"],
            {
                "id": None,
                "fecha_local": None,
                "tipo": "SALDO FINAL",
                "vale_id": None,
                "numero_entidad": None,
                "numero_estacion": None,
                "orden_numero": None,
                "variacion": estado_cuenta["saldo_final"],
                "saldo_posterior": None,
            },
        ]
    else:
        filas = await reportes.consumo_periodo(
            sesion,
            desde=desde,
            hasta=hasta,
            agrupacion=agrupacion,
            institucion_id=institucion_id,
            orden_id=orden_id,
            vale_id=vale_id,
            combustible_id=combustible_id,
            estado=estado,
            emisor=emisor,
        )
    columnas = list(filas[0]) if filas else ["sin_datos"]
    datos = xlsx.crear(
        reporte, columnas, filas or [{"sin_datos": "Sin registros para los filtros."}]
    )
    return StreamingResponse(
        BytesIO(datos),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{reporte}.xlsx"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )

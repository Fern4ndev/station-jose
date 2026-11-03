"""API para extraer, revisar y confirmar órdenes de compra desde documentos."""

import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import PurePath
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy import text

from app.config import obtener_settings
from app.core import archivos, dinero
from app.core.tiempo import hoy
from app.db.sesion import SesionBd
from app.dependencies import (
    UsuarioAutenticado,
    ip_de_peticion,
    requiere_permiso,
    user_agent_de_peticion,
)
from app.errors import ErrorDominio
from app.schemas.ocr import (
    ConfirmacionSalida,
    ConfirmarExtraccion,
    DescartarSalida,
    ExtraccionSalida,
    HistorialOcr,
    PrecisionOcr,
)
from app.services import auditoria, instituciones, ordenes, parametros
from app.services.ocr import extracciones, pipeline

router = APIRouter(prefix="/ocr", tags=["ocr"])
UsuarioOcr = Annotated[UsuarioAutenticado, Depends(requiere_permiso("ocr.usar"))]
UsuarioHistorialOcr = Annotated[UsuarioAutenticado, Depends(requiere_permiso("ocr.historial"))]
logger = logging.getLogger("app.routers.ocr")


def _es_admin(usuario: UsuarioAutenticado) -> bool:
    return usuario.rol == "administrador"


def _hay_datos_orden(datos: dict | None) -> bool:
    """Identifica candidatos estructurados que deben confirmarse junto a la orden."""
    if not datos:
        return False
    proveedor = datos.get("proveedor") or {}
    return any(
        (
            datos.get("numero_orden"),
            datos.get("numero_siaf"),
            datos.get("fecha"),
            proveedor.get("razon_social"),
            proveedor.get("ruc"),
            datos.get("sede_estacion"),
            datos.get("unidad_ejecutora"),
            datos.get("ruc_unidad_ejecutora"),
            datos.get("partidas_combustible"),
        )
    )


async def _obtener(
    sesion: SesionBd, id_extraccion: int, usuario: UsuarioAutenticado, *, bloquear: bool = False
) -> dict:
    return await extracciones.obtener(
        sesion,
        id_extraccion,
        usuario_id=usuario.id,
        administrador=_es_admin(usuario),
        bloquear=bloquear,
    )


async def _ejecutar(sesion: SesionBd, id_extraccion: int, contenido: bytes) -> ExtraccionSalida:
    await extracciones.procesando(sesion, id_extraccion)
    ajustes_app = obtener_settings()
    ajustes = pipeline.AjustesOcr(
        dpi=ajustes_app.ocr_dpi,
        tiempo_segundos=ajustes_app.ocr_tiempo_segundos,
        turno_segundos=ajustes_app.ocr_turno_segundos,
        concurrencia=ajustes_app.ocr_concurrencia,
    )
    try:
        lectura = await run_in_threadpool(pipeline.procesar, contenido, ajustes=ajustes)
    except ErrorDominio as error:
        await extracciones.marcar_fallida(sesion, id_extraccion, error.codigo, error.mensaje)
        if error.codigo == "OCR_OCUPADO":
            raise ErrorDominio(
                error.status_code, error.codigo, error.mensaje, {"extraccion_id": id_extraccion}
            ) from error
        registro = await extracciones.obtener(
            sesion, id_extraccion, usuario_id=-1, administrador=True
        )
        return _respuesta(registro)
    except Exception:
        logger.exception("Fallo inesperado del pipeline OCR para extracción %s", id_extraccion)
        await extracciones.marcar_fallida(
            sesion,
            id_extraccion,
            "OCR_ERROR_INTERNO",
            "No se pudo procesar el documento. Puede reintentarlo o registrar la orden manual.",
        )
        registro = await extracciones.obtener(
            sesion, id_extraccion, usuario_id=-1, administrador=True
        )
        return _respuesta(registro)

    sugerida = lectura.institucion_sugerida
    if sugerida:
        enlace = await instituciones.verificar_ruc(sesion, sugerida["ruc"])
        encontrada = enlace["institucion"]
        sugerida = {
            **sugerida,
            "institucion_id": encontrada["id"] if encontrada else None,
            "institucion_registrada": encontrada is not None,
        }
    campos = [asdict(campo) for campo in lectura.campos]
    confianzas = [campo.confianza for campo in lectura.campos]
    resultado = {
        "estado": lectura.estado,
        "metodo": lectura.metodo,
        "campos": campos,
        "institucion_sugerida": sugerida,
        "datos_orden": lectura.datos_orden,
        "advertencias": list(lectura.advertencias),
        "paginas": lectura.paginas,
        "tiempo_ms": lectura.tiempo_ms,
        "error_codigo": lectura.motivo or None,
        "error_detalle": "El documento no produjo datos suficientes."
        if lectura.estado == "fallida"
        else None,
        "confianza_promedio": sum(confianzas) / len(confianzas) if confianzas else None,
    }
    if lectura.estado == "fallida":
        resultado["estado"] = "fallida"
    await extracciones.guardar_resultado(sesion, id_extraccion, resultado)
    registro = await extracciones.obtener(sesion, id_extraccion, usuario_id=-1, administrador=True)
    return _respuesta(registro)


def _respuesta(registro: dict) -> ExtraccionSalida:
    resultado = registro["resultado"] or {}
    return ExtraccionSalida(
        id=int(registro["id"]),
        estado=str(registro["estado"]),
        metodo=registro["metodo"],
        campos=resultado.get("campos", []),
        institucion_sugerida=resultado.get("institucion_sugerida"),
        datos_orden=resultado.get("datos_orden"),
        advertencias=resultado.get("advertencias", []),
        error_codigo=registro["error_codigo"],
        error_detalle=registro["error_detalle"],
        paginas=resultado.get("paginas"),
        tiempo_ms=registro["tiempo_ms"],
        version_pipeline=registro["version_pipeline"],
        creado_en=registro["creado_en"],
    )


@router.post("/extracciones", response_model=ExtraccionSalida, status_code=201)
async def subir_documento(
    sesion: SesionBd,
    request: Request,
    usuario: UsuarioOcr,
    archivo: Annotated[UploadFile, File()],
) -> ExtraccionSalida:
    maximo = await parametros.numero(sesion, "archivo_max_mb") * 1024 * 1024
    contenido = await archivo.read(maximo + 1)
    validado = archivos.validar(
        contenido, uso="documento", formatos=("pdf", "jpg", "png"), maximo_bytes=maximo
    )
    nombre = (
        PurePath((archivo.filename or "documento").replace("\\", "/")).name[:255] or "documento"
    )
    guardado = await archivos.guardar_documento_ocr(
        validado.contenido, validado.extension, hoy().year
    )
    try:
        id_extraccion = await extracciones.crear(
            sesion,
            usuario_id=usuario.id,
            archivo_path=guardado.path_relativo,
            archivo_nombre=nombre,
            archivo_mime=guardado.media_type,
            archivo_hash=guardado.hash_sha256,
            archivo_tamano=guardado.tamano,
        )
        await auditoria.registrar(
            sesion,
            usuario_id=usuario.id,
            accion="ocr_subido",
            entidad="ocr_extracciones",
            entidad_id=id_extraccion,
            despues={"archivo": nombre},
            ip=ip_de_peticion(request),
            user_agent=user_agent_de_peticion(request),
        )
        await sesion.commit()
    except Exception:
        await sesion.rollback()
        await archivos.eliminar_documento(guardado.path_relativo)
        raise
    return await _ejecutar(sesion, id_extraccion, validado.contenido)


@router.get("/extracciones/{id_extraccion}", response_model=ExtraccionSalida)
async def detalle(
    id_extraccion: int,
    sesion: SesionBd,
    usuario: UsuarioOcr,
) -> ExtraccionSalida:
    return _respuesta(await _obtener(sesion, id_extraccion, usuario))


@router.get("/extracciones/{id_extraccion}/archivo")
async def ver_archivo(
    id_extraccion: int,
    sesion: SesionBd,
    usuario: UsuarioOcr,
) -> Response:
    registro = await _obtener(sesion, id_extraccion, usuario)
    contenido = await archivos.leer_documento_ocr(
        registro["archivo_path"], registro["archivo_hash"]
    )
    return Response(
        contenido,
        media_type=registro["archivo_mime"],
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(registro['archivo_nombre'])}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/extracciones/{id_extraccion}/reintentar", response_model=ExtraccionSalida, status_code=201
)
async def reintentar(
    id_extraccion: int,
    sesion: SesionBd,
    usuario: UsuarioOcr,
) -> ExtraccionSalida:
    anterior = await _obtener(sesion, id_extraccion, usuario, bloquear=True)
    if anterior["estado"] != "fallida":
        raise ErrorDominio(
            409, "EXTRACCION_NO_REINTENTABLE", "Solo se puede reintentar una extracción fallida."
        )
    # Reutiliza el original verificado y registra un nuevo intento enlazado al anterior.
    datos = await archivos.leer_documento_ocr(anterior["archivo_path"], anterior["archivo_hash"])
    nuevo_id = await extracciones.crear(
        sesion,
        usuario_id=usuario.id,
        archivo_path=anterior["archivo_path"],
        archivo_nombre=anterior["archivo_nombre"],
        archivo_mime=anterior["archivo_mime"],
        archivo_hash=anterior["archivo_hash"],
        archivo_tamano=anterior["archivo_tamano"],
        reintento_de_id=id_extraccion,
    )
    await sesion.commit()
    return await _ejecutar(sesion, nuevo_id, datos)


@router.post(
    "/extracciones/{id_extraccion}/confirmar", response_model=ConfirmacionSalida, status_code=201
)
async def confirmar(
    id_extraccion: int,
    peticion: ConfirmarExtraccion,
    request: Request,
    sesion: SesionBd,
    usuario: UsuarioOcr,
) -> ConfirmacionSalida:
    if not peticion.datos_revisados:
        raise ErrorDominio(
            409,
            "EXTRACCION_NO_CONFIRMABLE",
            "Debe revisar y confirmar los datos antes de crear la orden.",
        )
    registro = await _obtener(sesion, id_extraccion, usuario, bloquear=True)
    if registro["estado"] != "lista":
        raise ErrorDominio(
            409, "EXTRACCION_NO_CONFIRMABLE", "La extracción debe estar lista para confirmarse."
        )
    datos_extraidos = (registro["resultado"] or {}).get("datos_orden")
    if _hay_datos_orden(datos_extraidos) and peticion.datos_orden is None:
        raise ErrorDominio(
            409,
            "EXTRACCION_NO_CONFIRMABLE",
            "Debe enviar los datos estructurados revisados de la orden.",
        )
    orden_data = peticion.orden
    orden_id = await ordenes.crear(
        sesion,
        institucion_id=orden_data.institucion_id,
        numero=orden_data.numero,
        fecha_emision=date.fromisoformat(orden_data.fecha_emision),
        presupuesto_soles=dinero.monto(orden_data.presupuesto_soles),
        observaciones=orden_data.observaciones,
        combustible_id=orden_data.combustible_id,
        serie_desde=orden_data.serie_desde,
        serie_hasta=orden_data.serie_hasta,
        estado_inicial=orden_data.estado,
        actor_id=usuario.id,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
        confirmar_duplicado=orden_data.confirmar_duplicado,
    )
    institucion = await instituciones.buscar_por_id(sesion, orden_data.institucion_id)
    numero_final = await sesion.scalar(
        text("SELECT numero FROM ordenes_compra WHERE id=:id"), {"id": orden_id}
    )
    finales = {
        "numero_orden": str(numero_final),
        "fecha": orden_data.fecha_emision,
        "monto": orden_data.presupuesto_soles,
        "institucion": institucion["nombre"] if institucion else None,
        "institucion_ruc": institucion["ruc"] if institucion else None,
        "datos_orden": (
            peticion.datos_orden.model_dump(mode="json") if peticion.datos_orden else None
        ),
    }
    extraidos = {
        campo["clave"]: campo["valor"] for campo in (registro["resultado"] or {}).get("campos", [])
    }
    correcciones = {
        clave: {
            "extraido": extraidos.get(clave),
            "final": valor,
            "corregido": extraidos.get(clave) != valor,
        }
        for clave, valor in finales.items()
    }
    datos_orden_extraidos = (registro["resultado"] or {}).get("datos_orden")
    if finales["datos_orden"] is not None:
        correcciones["datos_orden"] = {
            "extraido": datos_orden_extraidos,
            "final": finales["datos_orden"],
            "corregido": datos_orden_extraidos != finales["datos_orden"],
        }
    await sesion.execute(
        text("""
            UPDATE ordenes_compra SET creada_con_ocr=true, archivo_path=:path,
                archivo_tipo=:mime, archivo_tamano=:tamano, archivo_hash=:hash,
                datos_documento_ocr=CAST(:datos_documento AS jsonb)
            WHERE id=:id
        """),
        {
            "path": registro["archivo_path"],
            "mime": registro["archivo_mime"],
            "tamano": registro["archivo_tamano"],
            "hash": registro["archivo_hash"],
            "datos_documento": json.dumps(finales["datos_orden"], ensure_ascii=False),
            "id": orden_id,
        },
    )
    await sesion.execute(
        text("""
        UPDATE ocr_extracciones SET estado='confirmada', orden_compra_id=:orden,
            campos_finales=CAST(:finales AS jsonb), correcciones=CAST(:correcciones AS jsonb)
        WHERE id=:id
    """),
        {
            "orden": orden_id,
            "finales": json.dumps(finales, ensure_ascii=False),
            "correcciones": json.dumps(correcciones, ensure_ascii=False),
            "id": id_extraccion,
        },
    )
    await auditoria.registrar(
        sesion,
        usuario_id=usuario.id,
        accion="ocr_confirmado",
        entidad="ocr_extracciones",
        entidad_id=id_extraccion,
        despues={"orden_id": orden_id, "correcciones": correcciones},
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return ConfirmacionSalida(extraccion_id=id_extraccion, orden_id=orden_id)


@router.post("/extracciones/{id_extraccion}/descartar", response_model=DescartarSalida)
async def descartar(
    id_extraccion: int,
    request: Request,
    sesion: SesionBd,
    usuario: UsuarioOcr,
) -> DescartarSalida:
    registro = await _obtener(sesion, id_extraccion, usuario, bloquear=True)
    if registro["estado"] not in ("lista", "fallida"):
        raise ErrorDominio(
            409, "EXTRACCION_NO_DESCARTABLE", "La extracción no está lista para descartarse."
        )
    await sesion.execute(
        text("UPDATE ocr_extracciones SET estado='descartada' WHERE id=:id"), {"id": id_extraccion}
    )
    await auditoria.registrar(
        sesion,
        usuario_id=usuario.id,
        accion="ocr_descartado",
        entidad="ocr_extracciones",
        entidad_id=id_extraccion,
        ip=ip_de_peticion(request),
        user_agent=user_agent_de_peticion(request),
    )
    await sesion.commit()
    return DescartarSalida(id=id_extraccion)


@router.get("/extracciones", response_model=HistorialOcr)
async def historial(
    sesion: SesionBd,
    usuario: UsuarioHistorialOcr,
    estado: Annotated[str | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HistorialOcr:
    items, total = await extracciones.listar(
        sesion,
        usuario_id=None,
        estado=estado,
        desde=desde,
        hasta=hasta,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return HistorialOcr(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


@router.get("/precision", response_model=PrecisionOcr)
async def precision(
    sesion: SesionBd,
    _: UsuarioHistorialOcr,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> PrecisionOcr:
    return PrecisionOcr(**(await extracciones.precision(sesion, desde=desde, hasta=hasta)))

"""Persistencia y reglas de ciclo de vida de las extracciones OCR."""

import json
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ErrorDominio

VERSION_PIPELINE = "ocr-sin-congelar"


async def crear(
    sesion: AsyncSession,
    *,
    usuario_id: int,
    archivo_path: str,
    archivo_nombre: str,
    archivo_mime: str,
    archivo_hash: str,
    archivo_tamano: int,
    reintento_de_id: int | None = None,
) -> int:
    resultado = await sesion.execute(
        text("""
        INSERT INTO ocr_extracciones
            (app_user_id, archivo_path, archivo_nombre, archivo_mime, archivo_hash,
             archivo_tamano, estado, reintento_de_id)
        VALUES (:usuario, :path, :nombre, :mime, :hash, :tamano, 'pendiente', :reintento)
        RETURNING id
    """),
        {
            "usuario": usuario_id,
            "path": archivo_path,
            "nombre": archivo_nombre,
            "mime": archivo_mime,
            "hash": archivo_hash,
            "tamano": archivo_tamano,
            "reintento": reintento_de_id,
        },
    )
    return int(resultado.scalar_one())


async def obtener(
    sesion: AsyncSession,
    id_extraccion: int,
    *,
    usuario_id: int,
    administrador: bool,
    bloquear: bool = False,
) -> dict:
    consulta = "SELECT * FROM ocr_extracciones WHERE id = :id"
    if bloquear:
        consulta = "SELECT * FROM ocr_extracciones WHERE id = :id FOR UPDATE"
    fila = (
        (
            await sesion.execute(
                text(consulta),
                {"id": id_extraccion},
            )
        )
        .mappings()
        .one_or_none()
    )
    if fila is None:
        raise ErrorDominio(404, "EXTRACCION_NO_ENCONTRADA", "La extracción OCR no existe.")
    registro = dict(fila)
    if not administrador and registro["app_user_id"] != usuario_id:
        raise ErrorDominio(404, "EXTRACCION_NO_ENCONTRADA", "La extracción OCR no existe.")
    return registro


async def procesando(sesion: AsyncSession, id_extraccion: int) -> None:
    resultado = await sesion.execute(
        text("""
        UPDATE ocr_extracciones SET estado='procesando'
        WHERE id=:id AND estado='pendiente'
    """),
        {"id": id_extraccion},
    )
    if resultado.rowcount != 1:
        raise ErrorDominio(409, "EXTRACCION_NO_PROCESABLE", "La extracción ya fue procesada.")
    await sesion.commit()


async def guardar_resultado(sesion: AsyncSession, id_extraccion: int, resultado: dict) -> None:
    await sesion.execute(
        text("""
        UPDATE ocr_extracciones SET estado=CAST(:estado AS ocr_status),
            metodo=CAST(:metodo AS ocr_method),
            resultado=CAST(:resultado AS jsonb), confianza_promedio=:confianza,
            tiempo_ms=:tiempo, version_pipeline=:version,
            error_codigo=:error_codigo, error_detalle=:error_detalle
        WHERE id=:id AND estado='procesando'
    """),
        {
            "id": id_extraccion,
            "estado": resultado["estado"],
            "metodo": resultado.get("metodo"),
            "resultado": json.dumps(resultado, ensure_ascii=False),
            "confianza": resultado.get("confianza_promedio"),
            "tiempo": resultado.get("tiempo_ms"),
            "version": VERSION_PIPELINE,
            "error_codigo": resultado.get("error_codigo"),
            "error_detalle": resultado.get("error_detalle"),
        },
    )
    await sesion.commit()


async def marcar_fallida(
    sesion: AsyncSession, id_extraccion: int, codigo: str, detalle: str
) -> None:
    await sesion.execute(
        text("""
        UPDATE ocr_extracciones SET estado='fallida', error_codigo=:codigo, error_detalle=:detalle,
            version_pipeline=:version WHERE id=:id
    """),
        {"id": id_extraccion, "codigo": codigo, "detalle": detalle, "version": VERSION_PIPELINE},
    )
    await sesion.commit()


async def listar(
    sesion: AsyncSession,
    *,
    usuario_id: int | None,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    pagina: int,
    por_pagina: int,
) -> tuple[list[dict], int]:
    params = {
        "usuario": usuario_id,
        "estado": estado,
        "desde": desde,
        "hasta": hasta,
        "limite": por_pagina,
        "offset": (pagina - 1) * por_pagina,
    }
    total = int(
        (
            await sesion.execute(
                text("""
                    SELECT count(*) FROM ocr_extracciones
                    WHERE (
                        CAST(:usuario AS bigint) IS NULL
                        OR app_user_id = CAST(:usuario AS bigint)
                    )
                      AND (CAST(:estado AS text) IS NULL OR estado::text = CAST(:estado AS text))
                      AND (CAST(:desde AS date) IS NULL OR creado_en::date >= CAST(:desde AS date))
                      AND (CAST(:hasta AS date) IS NULL OR creado_en::date <= CAST(:hasta AS date))
                """),
                params,
            )
        ).scalar_one()
    )
    filas = await sesion.execute(
        text(
            """
            SELECT id, app_user_id, archivo_nombre, estado, metodo, confianza_promedio,
                   tiempo_ms, error_codigo, orden_compra_id, creado_en
              FROM ocr_extracciones
            WHERE (
                CAST(:usuario AS bigint) IS NULL
                OR app_user_id = CAST(:usuario AS bigint)
            )
              AND (CAST(:estado AS text) IS NULL OR estado::text = CAST(:estado AS text))
              AND (CAST(:desde AS date) IS NULL OR creado_en::date >= CAST(:desde AS date))
              AND (CAST(:hasta AS date) IS NULL OR creado_en::date <= CAST(:hasta AS date))
            ORDER BY creado_en DESC, id DESC LIMIT :limite OFFSET :offset
            """
        ),
        params,
    )
    return [dict(fila) for fila in filas.mappings()], total


async def precision(sesion: AsyncSession, *, desde: date | None, hasta: date | None) -> dict:
    filas = await sesion.execute(
        text("""
        SELECT correcciones FROM ocr_extracciones
        WHERE estado='confirmada'
          AND (CAST(:desde AS date) IS NULL OR creado_en::date>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR creado_en::date<=CAST(:hasta AS date))
    """),
        {"desde": desde, "hasta": hasta},
    )
    cuentas: dict[str, list[int]] = {}
    total = 0
    for fila in filas.mappings():
        total += 1
        correcciones = fila["correcciones"] or {}
        for clave, cambio in correcciones.items():
            cuenta = cuentas.setdefault(clave, [0, 0])
            cuenta[0] += 1
            if cambio.get("corregido"):
                cuenta[1] += 1
    campos = {
        clave: {
            "evaluados": cuenta[0],
            "corregidos": cuenta[1],
            "precision": round((cuenta[0] - cuenta[1]) / cuenta[0], 4) if cuenta[0] else None,
        }
        for clave, cuenta in cuentas.items()
    }
    return {"total_confirmadas": total, "campos": campos}

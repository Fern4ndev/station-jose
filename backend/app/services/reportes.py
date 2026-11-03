"""Proyecciones para panel, reportes y exportación reutilizable."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import tiempo
from app.services import consultas, parametros


def rangos() -> dict:
    hoy = tiempo.hoy()
    inicio_semana, fin_semana = tiempo.rango_semana(hoy)
    inicio_mes, fin_mes = tiempo.rango_mes_actual()
    inicio_anterior, fin_anterior = tiempo.rango_mes_anterior()
    return {
        "hoy": {"desde": hoy, "hasta": hoy},
        "esta_semana": {
            "desde": inicio_semana.date(),
            "hasta": fin_semana.date() - timedelta(days=1),
        },
        "este_mes": {"desde": inicio_mes.date(), "hasta": fin_mes.date() - timedelta(days=1)},
        "mes_anterior": {
            "desde": inicio_anterior.date(),
            "hasta": fin_anterior.date() - timedelta(days=1),
        },
    }


async def consumo_periodo(sesion: AsyncSession, **filtros) -> list[dict]:
    return await consultas.consumo(sesion, **filtros)


async def consumo_instituciones(
    sesion: AsyncSession,
    *,
    desde: date | None,
    hasta: date | None,
    combustible_id: int | None = None,
) -> list[dict]:
    filas = await sesion.execute(
        text("""
        SELECT i.id AS institucion_id,i.nombre AS institucion,
               sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                        WHEN m.tipo='reversion' THEN -m.importe_soles
                        ELSE 0 END)::text AS importe_soles,
               sum(CASE WHEN m.tipo='consumo' THEN m.cantidad_galones
                        WHEN m.tipo='reversion' THEN -m.cantidad_galones
                        ELSE 0 END)::text AS galones
        FROM movimientos_vale m JOIN vales v ON v.id=m.vale_id
        JOIN ordenes_compra o ON o.id=v.orden_compra_id
        JOIN instituciones i ON i.id=o.institucion_id
        WHERE m.tipo IN ('consumo','reversion')
          AND (CAST(:desde AS date) IS NULL OR m.fecha_local>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR m.fecha_local<=CAST(:hasta AS date))
          AND (
              CAST(:combustible AS bigint) IS NULL
              OR v.combustible_id=CAST(:combustible AS bigint)
          )
        GROUP BY i.id,i.nombre ORDER BY sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                                                 ELSE -m.importe_soles END) DESC,i.nombre
    """),
        {"desde": desde, "hasta": hasta, "combustible": combustible_id},
    )
    return [dict(fila) for fila in filas.mappings()]


async def consumo_combustibles(
    sesion: AsyncSession,
    *,
    desde: date | None,
    hasta: date | None,
    institucion_id: int | None = None,
) -> list[dict]:
    filas = await sesion.execute(
        text("""
        SELECT c.id AS combustible_id,c.nombre AS combustible,
               sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                        WHEN m.tipo='reversion' THEN -m.importe_soles
                        ELSE 0 END)::text AS importe_soles,
               sum(CASE WHEN m.tipo='consumo' THEN m.cantidad_galones
                        WHEN m.tipo='reversion' THEN -m.cantidad_galones
                        ELSE 0 END)::text AS galones
        FROM movimientos_vale m JOIN vales v ON v.id=m.vale_id
        JOIN ordenes_compra o ON o.id=v.orden_compra_id
        JOIN combustibles c ON c.id=v.combustible_id
        WHERE m.tipo IN ('consumo','reversion')
          AND (CAST(:desde AS date) IS NULL OR m.fecha_local>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR m.fecha_local<=CAST(:hasta AS date))
          AND (
              CAST(:institucion AS bigint) IS NULL
              OR o.institucion_id=CAST(:institucion AS bigint)
          )
        GROUP BY c.id,c.nombre ORDER BY sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                                                 ELSE -m.importe_soles END) DESC,c.nombre
    """),
        {"desde": desde, "hasta": hasta, "institucion": institucion_id},
    )
    return [dict(fila) for fila in filas.mappings()]


async def ordenes_periodo(
    sesion: AsyncSession,
    *,
    desde: date | None,
    hasta: date | None,
    institucion_id: int | None = None,
) -> dict:
    filas = await sesion.execute(
        text("""
        SELECT i.id AS institucion_id,i.nombre AS institucion,count(*)::int AS cantidad_ordenes,
               coalesce(sum(o.presupuesto_soles),0)::text AS presupuesto_soles
        FROM ordenes_compra o JOIN instituciones i ON i.id=o.institucion_id
        WHERE (CAST(:desde AS date) IS NULL OR o.fecha_emision>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR o.fecha_emision<=CAST(:hasta AS date))
          AND (
              CAST(:institucion AS bigint) IS NULL
              OR o.institucion_id=CAST(:institucion AS bigint)
          )
        GROUP BY i.id,i.nombre ORDER BY i.nombre
    """),
        {"desde": desde, "hasta": hasta, "institucion": institucion_id},
    )
    instituciones = [dict(fila) for fila in filas.mappings()]
    presupuesto_total = sum((Decimal(f["presupuesto_soles"]) for f in instituciones), Decimal("0"))
    return {
        "total_ordenes": sum(f["cantidad_ordenes"] for f in instituciones),
        "presupuesto_total_soles": f"{presupuesto_total:.2f}",
        "instituciones": instituciones,
    }


async def indicadores(sesion: AsyncSession) -> dict:
    hoy = tiempo.hoy()
    inicio_mes = tiempo.rango_mes_actual()[0].date()
    umbral_saldo = await parametros.numero(sesion, "vale_umbral_saldo_bajo_pct")
    dias_aviso = await parametros.numero(sesion, "vale_dias_aviso_vencimiento")
    fila = (
        (
            await sesion.execute(
                text("""
        SELECT (SELECT count(*)::int FROM ordenes_compra
                 WHERE fecha_emision>=:inicio AND fecha_emision<=:hoy) AS ordenes_mes,
               (SELECT count(*)::int FROM vales WHERE estado='activo') AS vales_activos,
               (SELECT coalesce(sum(CASE WHEN tipo='consumo' THEN cantidad_galones
                         WHEN tipo='reversion' THEN -cantidad_galones ELSE 0 END),0)::text
                  FROM movimientos_vale WHERE tipo IN ('consumo','reversion')
                    AND fecha_local>=:inicio AND fecha_local<=:hoy) AS galones_mes,
               (SELECT count(*)::int FROM vales WHERE estado='activo'
                    AND saldo<=cantidad_inicial*CAST(:umbral AS numeric)/100) AS vales_saldo_bajo,
               (SELECT count(*)::int FROM vales WHERE estado='activo'
                    AND fecha_vencimiento BETWEEN :hoy AND :aviso) AS vales_por_vencer
    """),
                {
                    "inicio": inicio_mes,
                    "hoy": hoy,
                    "aviso": hoy + timedelta(days=dias_aviso),
                    "umbral": umbral_saldo,
                },
            )
        )
        .mappings()
        .one()
    )
    return dict(fila)

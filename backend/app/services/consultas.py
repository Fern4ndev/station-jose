"""Consultas derivadas siempre desde los movimientos confirmados."""

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ErrorDominio


async def saldo_orden(sesion: AsyncSession, orden_id: int) -> dict:
    orden = (
        (
            await sesion.execute(
                text("""
        SELECT o.id, o.institucion_id, i.nombre AS institucion, o.numero,
               o.anio, o.estado, o.presupuesto_soles::text AS presupuesto_soles
        FROM ordenes_compra o JOIN instituciones i ON i.id=o.institucion_id
        WHERE o.id=:id
    """),
                {"id": orden_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if orden is None:
        raise ErrorDominio(404, "ORDEN_NO_ENCONTRADA", "La orden de compra no existe.")
    vales = (
        (
            await sesion.execute(
                text("""
        SELECT v.id, v.numero_estacion, v.numero_entidad, v.emisor::text AS emisor,
               v.combustible_id, c.nombre AS combustible, v.estado::text AS estado,
               v.cantidad_inicial::text AS cantidad_inicial, v.saldo::text AS saldo,
               v.valor_comprometido_soles::text AS valor_comprometido_soles,
               coalesce(sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                                 WHEN m.tipo='reversion' THEN -m.importe_soles ELSE 0 END),
                        0)::text AS consumido_soles,
               coalesce(sum(CASE WHEN m.tipo='consumo' THEN m.cantidad_galones
                                 WHEN m.tipo='reversion' THEN -m.cantidad_galones ELSE 0 END),
                        0)::text AS consumido_galones
        FROM vales v JOIN combustibles c ON c.id=v.combustible_id
        LEFT JOIN movimientos_vale m ON m.vale_id=v.id
        WHERE v.orden_compra_id=:id
        GROUP BY v.id,c.nombre ORDER BY v.id
    """),
                {"id": orden_id},
            )
        )
        .mappings()
        .all()
    )
    emitido = sum(
        (Decimal(v["valor_comprometido_soles"]) for v in vales),
        Decimal("0.00"),
    )
    consumido = sum((Decimal(v["consumido_soles"]) for v in vales), Decimal("0.00"))
    presupuesto = Decimal(orden["presupuesto_soles"])
    return {
        "orden": dict(orden),
        "vales": [dict(v) for v in vales],
        "emitido_soles": f"{emitido:.2f}",
        "consumido_soles": f"{consumido:.2f}",
        "presupuesto_restante_soles": f"{max(Decimal('0.00'), presupuesto-emitido):.2f}",
    }


async def saldo_institucion(sesion: AsyncSession, institucion_id: int) -> dict:
    institucion = (
        (
            await sesion.execute(
                text("""
        SELECT id,nombre,ruc FROM instituciones WHERE id=:id
    """),
                {"id": institucion_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if institucion is None:
        raise ErrorDominio(404, "INSTITUCION_INEXISTENTE", "La institución no existe.")
    filas = await sesion.execute(
        text("""
        SELECT o.id AS orden_id,o.numero,o.anio,o.estado::text AS estado,
               o.presupuesto_soles::text AS presupuesto_soles,
               v.id AS vale_id,v.numero_estacion,v.numero_entidad,
               v.estado::text AS estado_vale,v.saldo::text AS saldo_galones,
               v.valor_comprometido_soles::text AS compromiso_soles,
               v.valor_soles::text AS emitido_soles
        FROM ordenes_compra o LEFT JOIN vales v ON v.orden_compra_id=o.id
        WHERE o.institucion_id=:institucion
        ORDER BY o.fecha_emision DESC,o.id DESC,v.id
    """),
        {"institucion": institucion_id},
    )
    items = [dict(fila) for fila in filas.mappings()]
    vigentes = [item for item in items if item["vale_id"] and item["estado_vale"] == "activo"]
    saldo_galones = sum((Decimal(v["saldo_galones"]) for v in vigentes), Decimal("0"))
    compromiso_soles = sum((Decimal(v["compromiso_soles"]) for v in vigentes), Decimal("0"))
    return {
        "institucion": dict(institucion),
        "ordenes": items,
        "saldo_vigente_galones": f"{saldo_galones:.2f}",
        "compromiso_vigente_soles": f"{compromiso_soles:.2f}",
    }


async def consumo(
    sesion: AsyncSession,
    *,
    institucion_id: int | None,
    orden_id: int | None,
    vale_id: int | None,
    combustible_id: int | None,
    estado: str | None,
    emisor: str | None,
    desde: date | None,
    hasta: date | None,
    agrupacion: str,
) -> list[dict]:
    query = text("""
        SELECT CASE :agrupacion
                 WHEN 'dia' THEN m.fecha_local
                 WHEN 'semana' THEN date_trunc('week',m.fecha_local)::date
                 ELSE date_trunc('month',m.fecha_local)::date
               END AS periodo, o.institucion_id, v.combustible_id,
               v.emisor::text AS emisor,
               sum(CASE WHEN m.tipo='consumo' THEN m.importe_soles
                        WHEN m.tipo='reversion' THEN -m.importe_soles ELSE 0 END)::text
                   AS importe_soles,
               sum(CASE WHEN m.tipo='consumo' THEN m.cantidad_galones
                        WHEN m.tipo='reversion' THEN -m.cantidad_galones ELSE 0 END)::text
                   AS galones
        FROM movimientos_vale m JOIN vales v ON v.id=m.vale_id
        JOIN ordenes_compra o ON o.id=v.orden_compra_id
        WHERE m.tipo IN ('consumo','reversion')
          AND (
              CAST(:institucion AS bigint) IS NULL
              OR o.institucion_id=CAST(:institucion AS bigint)
          )
          AND (CAST(:orden AS bigint) IS NULL OR v.orden_compra_id=CAST(:orden AS bigint))
          AND (CAST(:vale AS bigint) IS NULL OR v.id=CAST(:vale AS bigint))
          AND (
              CAST(:combustible AS bigint) IS NULL
              OR v.combustible_id=CAST(:combustible AS bigint)
          )
          AND (CAST(:estado AS text) IS NULL OR v.estado::text=CAST(:estado AS text))
          AND (CAST(:emisor AS text) IS NULL OR v.emisor::text=CAST(:emisor AS text))
          AND (CAST(:desde AS date) IS NULL OR m.fecha_local>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR m.fecha_local<=CAST(:hasta AS date))
        GROUP BY periodo,o.institucion_id,v.combustible_id,v.emisor
        ORDER BY periodo
    """)
    params = {
        "agrupacion": agrupacion,
        "institucion": institucion_id,
        "orden": orden_id,
        "vale": vale_id,
        "combustible": combustible_id,
        "estado": estado,
        "emisor": emisor,
        "desde": desde,
        "hasta": hasta,
    }
    filas = await sesion.execute(query, params)
    return [dict(fila) for fila in filas.mappings()]


async def estado_cuenta(
    sesion: AsyncSession, institucion_id: int, *, desde: date | None, hasta: date | None
) -> dict:
    existe = await sesion.scalar(
        text("SELECT 1 FROM instituciones WHERE id=:id"), {"id": institucion_id}
    )
    if existe is None:
        raise ErrorDominio(404, "INSTITUCION_INEXISTENTE", "La institución no existe.")
    inicial = await sesion.scalar(
        text("""
        SELECT coalesce(sum(m.variacion),0)::text FROM movimientos_vale m
        JOIN vales v ON v.id=m.vale_id JOIN ordenes_compra o ON o.id=v.orden_compra_id
        WHERE o.institucion_id=:institucion
          AND CAST(:desde AS date) IS NOT NULL
          AND m.fecha_local<CAST(:desde AS date)
    """),
        {"institucion": institucion_id, "desde": desde},
    )
    filas = await sesion.execute(
        text("""
        SELECT m.id,m.fecha_local,m.tipo::text AS tipo,m.vale_id,
               v.numero_entidad,v.numero_estacion,o.numero AS orden_numero,
               m.variacion::text AS variacion,m.saldo_posterior::text AS saldo_posterior
        FROM movimientos_vale m JOIN vales v ON v.id=m.vale_id
        JOIN ordenes_compra o ON o.id=v.orden_compra_id
        WHERE o.institucion_id=:institucion
          AND (CAST(:desde AS date) IS NULL OR m.fecha_local>=CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL OR m.fecha_local<=CAST(:hasta AS date))
        ORDER BY m.fecha_local,m.id
    """),
        {"institucion": institucion_id, "desde": desde, "hasta": hasta},
    )
    movimientos = [dict(fila) for fila in filas.mappings()]
    saldo_inicial = Decimal(inicial or "0")
    variacion = sum((Decimal(m["variacion"]) for m in movimientos), Decimal("0"))
    return {
        "institucion_id": institucion_id,
        "desde": desde,
        "hasta": hasta,
        "saldo_inicial": f"{saldo_inicial:.2f}",
        "movimientos": movimientos,
        "saldo_final": f"{saldo_inicial+variacion:.2f}",
    }

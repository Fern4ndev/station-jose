"""Integridad de saldos (AUD-05/AUD-06, Fase 8).

`verificar` compara en una sola consulta el saldo almacenado en `vales` con la
suma de las variaciones de sus movimientos: cualquier cambio de saldo nace de
un movimiento, así que la suma debe cuadrar exactamente. Cada corrida queda en
`verificaciones_integridad` y cada descuadre en `diferencias_integridad`.

El aviso no se repite en cada corrida:

- si el vale ya tiene una diferencia pendiente, se refrescan los saldos
  comparados (el índice único parcial impide tener dos alertas abiertas);
- si la última diferencia se revisó con los mismos saldos, no se vuelve a
  avisar: la diferencia no cambió y alguien ya la aceptó;
- si los saldos cambiaron o el descuadre reaparece tras una corrección, se
  crea una diferencia nueva, que es la que el administrador debe revisar.
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero
from app.errors import ErrorDominio
from app.services import auditoria

# Límite de paginación: ninguna consulta de bitácora trae de más.
MAXIMA_POR_PAGINA = 100

# Una sola pasada: cuenta los vales revisados y devuelve, como texto exacto,
# los que no cuadran con la suma de sus movimientos.
_CONSULTA_DETECCION = text(
    """
    WITH revisados AS (
        SELECT v.id AS vale_id,
               v.saldo,
               COALESCE(SUM(m.variacion), 0)::numeric(12,2) AS recalculado
        FROM vales v
        LEFT JOIN movimientos_vale m ON m.vale_id = v.id
        GROUP BY v.id
    )
    SELECT (SELECT count(*) FROM revisados) AS vales_revisados,
           COALESCE(
               (SELECT jsonb_agg(
                           jsonb_build_object(
                               'vale_id', r.vale_id,
                               'saldo_almacenado', r.saldo::text,
                               'saldo_recalculado', r.recalculado::text
                           )
                           ORDER BY r.vale_id
                       )
                FROM revisados r
                WHERE r.saldo <> r.recalculado),
               '[]'::jsonb
           ) AS diferencias
    """
)


def _jsonb(valor: Any) -> Any:
    """`asyncpg` entrega `jsonb` como texto; se normaliza a objetos Python."""
    if valor is None or isinstance(valor, dict | list):
        return valor
    return json.loads(valor)


def _diferencia(fila: Any) -> dict:
    """Fila de `diferencias_integridad` lista para el JSON de la API."""
    return {
        "id": int(fila["id"]),
        "verificacion_id": int(fila["verificacion_id"]),
        "vale_id": int(fila["vale_id"]),
        "numero_estacion": fila["numero_estacion"],
        "emisor": fila["emisor"],
        "saldo_almacenado": dinero.como_texto(fila["saldo_almacenado"]),
        "saldo_recalculado": dinero.como_texto(fila["saldo_recalculado"]),
        "diferencia": dinero.como_texto(
            fila["saldo_almacenado"] - fila["saldo_recalculado"]
        ),
        "revisada": bool(fila["revisada"]),
        "revisada_por": fila["revisada_por"],
        "revisada_por_nombre": fila["revisada_por_nombre"],
        "revisada_en": fila["revisada_en"],
        "comentario": fila["comentario"],
        "creado_en": fila["creado_en"],
    }


def _verificacion(fila: Any) -> dict:
    """Fila de `verificaciones_integridad` lista para el JSON de la API."""
    return {
        "id": int(fila["id"]),
        "ejecutada_por": fila["ejecutada_por"],
        "ejecutada_por_nombre": fila["ejecutada_por_nombre"],
        "vales_revisados": int(fila["vales_revisados"]),
        "diferencias": int(fila["diferencias"]),
        "creado_en": fila["creado_en"],
    }


async def _registrar_diferencia(
    sesion: AsyncSession, verificacion_id: int, detectada: dict
) -> None:
    """Abre o refresca la alerta del vale, salvo que ya esté aceptada igual.

    La última diferencia del vale decide: si está revisada y los saldos
    comparados no cambiaron, el descuadre es el mismo que ya revisó el
    administrador y no se repite. En cualquier otro caso el `INSERT` choca con
    el índice único parcial y refresca la alerta pendiente con los saldos de
    esta corrida.
    """
    ultima = (
        await sesion.execute(
            text(
                """
                SELECT revisada,
                       saldo_almacenado = CAST(:almacenado AS numeric)
                       AND saldo_recalculado = CAST(:recalculado AS numeric) AS sin_cambios
                FROM diferencias_integridad
                WHERE vale_id = :vale
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {
                "vale": detectada["vale_id"],
                "almacenado": detectada["saldo_almacenado"],
                "recalculado": detectada["saldo_recalculado"],
            },
        )
    ).mappings().first()
    if ultima is not None and ultima["revisada"] and ultima["sin_cambios"]:
        return

    await sesion.execute(
        text(
            """
            INSERT INTO diferencias_integridad
                (verificacion_id, vale_id, saldo_almacenado, saldo_recalculado)
            VALUES (:verificacion, :vale, :almacenado, :recalculado)
            ON CONFLICT (vale_id) WHERE NOT revisada
            DO UPDATE SET
                verificacion_id = EXCLUDED.verificacion_id,
                saldo_almacenado = EXCLUDED.saldo_almacenado,
                saldo_recalculado = EXCLUDED.saldo_recalculado
            """
        ),
        {
            "verificacion": verificacion_id,
            "vale": detectada["vale_id"],
            "almacenado": detectada["saldo_almacenado"],
            "recalculado": detectada["saldo_recalculado"],
        },
    )


async def verificar(
    sesion: AsyncSession,
    *,
    actor_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """AUD-05: recorre los saldos, registra la corrida y devuelve el resumen."""
    fila = (await sesion.execute(_CONSULTA_DETECCION)).mappings().one()
    detectadas = [dict(diferencia) for diferencia in _jsonb(fila["diferencias"])]

    verificacion = (
        await sesion.execute(
            text(
                """
                WITH nueva AS (
                    INSERT INTO verificaciones_integridad
                        (ejecutada_por, vales_revisados, diferencias)
                    VALUES (:actor, :revisados, :diferencias)
                    RETURNING id, ejecutada_por, vales_revisados, diferencias, creado_en
                )
                SELECT n.id, n.ejecutada_por, n.vales_revisados, n.diferencias,
                       n.creado_en, u.full_name AS ejecutada_por_nombre
                FROM nueva n
                LEFT JOIN app_users u ON u.id = n.ejecutada_por
                """
            ),
            {
                "actor": actor_id,
                "revisados": int(fila["vales_revisados"]),
                "diferencias": len(detectadas),
            },
        )
    ).mappings().one()

    for detectada in detectadas:
        await _registrar_diferencia(sesion, int(verificacion["id"]), detectada)

    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="verificacion_integridad",
        entidad="integridad",
        entidad_id=int(verificacion["id"]),
        despues={
            "vales_revisados": int(verificacion["vales_revisados"]),
            "diferencias": int(verificacion["diferencias"]),
        },
        ip=ip,
        user_agent=user_agent,
    )
    return {
        "id": int(verificacion["id"]),
        "ejecutada_por": verificacion["ejecutada_por"],
        "ejecutada_por_nombre": verificacion["ejecutada_por_nombre"],
        "vales_revisados": int(verificacion["vales_revisados"]),
        "diferencias": int(verificacion["diferencias"]),
        "creado_en": verificacion["creado_en"],
    }


async def pendientes(sesion: AsyncSession) -> int:
    """AUD-06: diferencias sin revisar, para el panel del administrador."""
    return int(
        (
            await sesion.execute(
                text("SELECT count(*) FROM diferencias_integridad WHERE NOT revisada")
            )
        ).scalar_one()
    )


async def ultima(sesion: AsyncSession) -> dict | None:
    """AUD-05: la última verificación con el nombre de quien la ejecutó."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT v.id, v.ejecutada_por, v.vales_revisados, v.diferencias,
                       v.creado_en, u.full_name AS ejecutada_por_nombre
                FROM verificaciones_integridad v
                LEFT JOIN app_users u ON u.id = v.ejecutada_por
                ORDER BY v.id DESC
                LIMIT 1
                """
            )
        )
    ).mappings().first()
    return None if fila is None else _verificacion(fila)


async def verificaciones(
    sesion: AsyncSession, *, pagina: int = 1, por_pagina: int = 20
) -> tuple[list[dict], int]:
    """AUD-05: historial paginado de verificaciones, la más reciente primero."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)
    total = int(
        (
            await sesion.execute(text("SELECT count(*) FROM verificaciones_integridad"))
        ).scalar_one()
    )
    filas = await sesion.execute(
        text(
            """
            SELECT v.id, v.ejecutada_por, v.vales_revisados, v.diferencias,
                   v.creado_en, u.full_name AS ejecutada_por_nombre
            FROM verificaciones_integridad v
            LEFT JOIN app_users u ON u.id = v.ejecutada_por
            ORDER BY v.id DESC
            LIMIT :limite OFFSET :desplazamiento
            """
        ),
        {"limite": por_pagina, "desplazamiento": (pagina - 1) * por_pagina},
    )
    return [_verificacion(fila) for fila in filas.mappings()], total


async def listar_diferencias(
    sesion: AsyncSession,
    *,
    revisada: bool | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> tuple[list[dict], int]:
    """AUD-06: diferencias detectadas, con el vale al que pertenecen."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)

    total = int(
        (
            await sesion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM diferencias_integridad d
                    WHERE (CAST(:revisada AS boolean) IS NULL
                           OR d.revisada = CAST(:revisada AS boolean))
                    """
                ),
                {"revisada": revisada},
            )
        ).scalar_one()
    )
    consulta = text(
        """
        SELECT d.id, d.verificacion_id, d.vale_id, d.saldo_almacenado,
               d.saldo_recalculado, d.revisada, d.revisada_por,
               d.revisada_en, d.comentario, d.creado_en,
               v.numero_estacion, v.emisor::text AS emisor,
               u.full_name AS revisada_por_nombre
        FROM diferencias_integridad d
        JOIN vales v ON v.id = d.vale_id
        LEFT JOIN app_users u ON u.id = d.revisada_por
        WHERE (CAST(:revisada AS boolean) IS NULL
               OR d.revisada = CAST(:revisada AS boolean))
        ORDER BY d.revisada, d.id DESC
        LIMIT :limite OFFSET :desplazamiento
        """
    )
    filas = await sesion.execute(
        consulta,
        {
            "revisada": revisada,
            "limite": por_pagina,
            "desplazamiento": (pagina - 1) * por_pagina,
        },
    )
    return [_diferencia(fila) for fila in filas.mappings()], total


async def ficha(sesion: AsyncSession, diferencia_id: int) -> dict:
    """Diferencia concreta con el vale y el revisor; 404 si no existe."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT d.id, d.verificacion_id, d.vale_id, d.saldo_almacenado,
                       d.saldo_recalculado, d.revisada, d.revisada_por,
                       d.revisada_en, d.comentario, d.creado_en,
                       v.numero_estacion, v.emisor::text AS emisor,
                       u.full_name AS revisada_por_nombre
                FROM diferencias_integridad d
                JOIN vales v ON v.id = d.vale_id
                LEFT JOIN app_users u ON u.id = d.revisada_por
                WHERE d.id = :id
                """
            ),
            {"id": diferencia_id},
        )
    ).mappings().first()
    if fila is None:
        raise ErrorDominio(
            404, "DIFERENCIA_NO_ENCONTRADA", "La diferencia no existe."
        )
    return _diferencia(fila)


async def revisar(
    sesion: AsyncSession,
    diferencia_id: int,
    *,
    comentario: str,
    actor_id: int,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """AUD-06: cierra una diferencia con el comentario del revisor.

    El bloqueo de la fila evita que dos revisores marquen la misma diferencia:
    el segundo encuentra `revisada = true` y recibe 409.
    """
    texto_comentario = comentario.strip()
    if not texto_comentario:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {"comentario": ["Indique el motivo de la revisión."]},
        )

    fila = (
        await sesion.execute(
            text(
                "SELECT id, revisada FROM diferencias_integridad WHERE id = :id FOR UPDATE"
            ),
            {"id": diferencia_id},
        )
    ).mappings().first()
    if fila is None:
        raise ErrorDominio(
            404, "DIFERENCIA_NO_ENCONTRADA", "La diferencia no existe."
        )
    if fila["revisada"]:
        raise ErrorDominio(
            409, "DIFERENCIA_YA_REVISADA", "Esa diferencia ya fue revisada."
        )

    await sesion.execute(
        text(
            """
            UPDATE diferencias_integridad
            SET revisada = TRUE,
                revisada_por = :actor,
                revisada_en = now(),
                comentario = :comentario
            WHERE id = :id
            """
        ),
        {
            "id": diferencia_id,
            "actor": actor_id,
            "comentario": texto_comentario,
        },
    )
    ficha_revisada = await ficha(sesion, diferencia_id)
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="diferencia_revisada",
        entidad="diferencias_integridad",
        entidad_id=diferencia_id,
        antes={
            "saldo_almacenado": ficha_revisada["saldo_almacenado"],
            "saldo_recalculado": ficha_revisada["saldo_recalculado"],
        },
        despues={"comentario": texto_comentario},
        ip=ip,
        user_agent=user_agent,
    )
    return ficha_revisada

"""Bitácora inmutable de acciones (AUD-01) y su lectura (AUD-03/AUD-04).

`registrar(...)` es la única puerta de escritura en `auditoria`; la usan
los servicios y los endpoints de la API. La tabla rechaza UPDATE y DELETE
mediante disparadores migrados, así que la huella no se puede alterar.

`listar_bitacora` alimenta la consulta con filtros y paginación (AUD-03) y
`historial` la línea de tiempo de un registro concreto (AUD-04). Los nombres
de entidad que usa el plan son singulares y los que escribe cada servicio
varían (`app_user`, `ordenes_compra`, `instituciones`), así que aquí se
traducen en un solo lugar.
"""

import json
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Límite de paginación: ninguna consulta de bitácora trae de más.
MAXIMA_POR_PAGINA = 100

# AUD-04: entidad del historial → nombres con los que los servicios auditan.
ENTIDADES_HISTORIAL: dict[str, tuple[str, ...]] = {
    "orden": ("ordenes_compra",),
    "vale": ("vales",),
    "institucion": ("instituciones",),
    "usuario": ("app_user",),
    "combustible": ("combustible",),
}


def _jsonb(valor: Any) -> str | None:
    """Serializa el antes/después para el cast a `jsonb`."""
    if valor is None:
        return None
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str)


def _jsonb_leido(valor: Any) -> Any:
    """`asyncpg` entrega `jsonb` como texto; lo devuelve como objeto Python."""
    if valor is None or isinstance(valor, dict | list):
        return valor
    return json.loads(valor)


def _fila(fila: Any) -> dict:
    """Fila de `auditoria` lista para el JSON de la API."""
    return {
        "id": int(fila["id"]),
        "app_user_id": fila["app_user_id"],
        "usuario": fila["usuario"],
        "accion": fila["accion"],
        "entidad": fila["entidad"],
        "entidad_id": fila["entidad_id"],
        "antes": _jsonb_leido(fila["antes"]),
        "despues": _jsonb_leido(fila["despues"]),
        "ip": None if fila["ip"] is None else str(fila["ip"]),
        "user_agent": fila["user_agent"],
        "creado_en": fila["creado_en"],
    }


def nombres_de_entidad(entidad: str) -> tuple[str, ...]:
    """Nombres auditados que corresponden a la entidad del plan."""
    return ENTIDADES_HISTORIAL.get(entidad, (entidad,))



def ip_valida(ip: str | None) -> str | None:
    """Solo deja pasar direcciones válidas para la columna `inet`."""
    if not ip:
        return None
    try:
        import ipaddress

        return ipaddress.ip_address(ip.strip()).compressed
    except ValueError:
        return None


async def registrar(
    sesion: AsyncSession,
    *,
    usuario_id: int | None,
    accion: str,
    entidad: str,
    entidad_id: int | str | None = None,
    antes: dict[str, Any] | None = None,
    despues: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Deja huella de la acción con usuario, entidad y valores del cambio."""
    await sesion.execute(
        text(
            """
            INSERT INTO auditoria
                (app_user_id, accion, entidad, entidad_id, antes, despues, ip, user_agent)
            VALUES
                (:usuario_id, :accion, :entidad, CAST(:entidad_id AS text),
                 CAST(:antes AS jsonb), CAST(:despues AS jsonb),
                 CAST(:ip AS inet), :user_agent)
            """
        ),
        {
            "usuario_id": usuario_id,
            "accion": accion,
            "entidad": entidad,
            "entidad_id": str(entidad_id) if entidad_id is not None else None,
            "antes": _jsonb(antes),
            "despues": _jsonb(despues),
            "ip": ip_valida(ip),
            "user_agent": user_agent,
        },
    )


async def listar_bitacora(
    sesion: AsyncSession,
    *,
    usuario_id: int | None = None,
    accion: str | None = None,
    entidad: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> tuple[list[dict], int]:
    """AUD-03: bitácora filtrada por usuario, acción, entidad y fechas."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)
    filtros = {
        "usuario": usuario_id,
        "accion": accion,
        "entidad": entidad,
        "desde": desde,
        "hasta": hasta,
    }
    # Filtros opcionales en una sola consulta: el parámetro nulo desactiva su
    # condición, así no se concatena SQL y los índices siguen disponibles.
    total = int(
        (
            await sesion.execute(
                text(
                    """
                    SELECT count(*)
                    FROM auditoria a
                    WHERE (CAST(:usuario AS bigint) IS NULL
                           OR a.app_user_id = CAST(:usuario AS bigint))
                      AND (CAST(:accion AS text) IS NULL
                           OR a.accion = CAST(:accion AS text))
                      AND (CAST(:entidad AS text) IS NULL
                           OR a.entidad = CAST(:entidad AS text))
                      AND (CAST(:desde AS date) IS NULL
                           OR a.creado_en >= CAST(:desde AS date))
                      AND (CAST(:hasta AS date) IS NULL
                           OR a.creado_en < CAST(:hasta AS date) + interval '1 day')
                    """
                ),
                filtros,
            )
        ).scalar_one()
    )
    consulta = text(
        """
        SELECT a.id, a.app_user_id, a.accion, a.entidad, a.entidad_id,
               a.antes, a.despues, a.ip, a.user_agent, a.creado_en,
               u.full_name AS usuario
        FROM auditoria a
        LEFT JOIN app_users u ON u.id = a.app_user_id
        WHERE (CAST(:usuario AS bigint) IS NULL
               OR a.app_user_id = CAST(:usuario AS bigint))
          AND (CAST(:accion AS text) IS NULL
               OR a.accion = CAST(:accion AS text))
          AND (CAST(:entidad AS text) IS NULL
               OR a.entidad = CAST(:entidad AS text))
          AND (CAST(:desde AS date) IS NULL
               OR a.creado_en >= CAST(:desde AS date))
          AND (CAST(:hasta AS date) IS NULL
               OR a.creado_en < CAST(:hasta AS date) + interval '1 day')
        ORDER BY a.id DESC
        LIMIT :limite OFFSET :desplazamiento
        """
    )
    filas = await sesion.execute(
        consulta,
        {
            **filtros,
            "limite": por_pagina,
            "desplazamiento": (pagina - 1) * por_pagina,
        },
    )
    return [_fila(fila) for fila in filas.mappings()], total


async def historial(
    sesion: AsyncSession,
    *,
    entidad: str,
    entidad_id: int,
    limite: int = 200,
) -> list[dict]:
    """AUD-04: línea de tiempo del registro, de lo más reciente a lo más viejo."""
    filas = await sesion.execute(
        text(
            """
            SELECT a.id, a.app_user_id, a.accion, a.entidad, a.entidad_id,
                   a.antes, a.despues, a.ip, a.user_agent, a.creado_en,
                   u.full_name AS usuario
            FROM auditoria a
            LEFT JOIN app_users u ON u.id = a.app_user_id
            WHERE a.entidad = ANY(CAST(:nombres AS text[]))
              AND a.entidad_id = CAST(:entidad_id AS text)
            ORDER BY a.id DESC
            LIMIT :limite
            """
        ),
        {
            "nombres": list(nombres_de_entidad(entidad)),
            "entidad_id": str(entidad_id),
            "limite": min(max(limite, 1), 500),
        },
    )
    return [_fila(fila) for fila in filas.mappings()]

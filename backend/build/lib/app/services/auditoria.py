"""Bitácora inmutable de acciones (AUD-01).

`registrar(...)` es la única puerta de escritura en `auditoria`; la usan
los servicios y los endpoints de la API. La tabla rechaza UPDATE y DELETE
mediante disparadores migrados, así que la huella no se puede alterar.
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _jsonb(valor: Any) -> str | None:
    """Serializa el antes/después para el cast a `jsonb`."""
    if valor is None:
        return None
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str)


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

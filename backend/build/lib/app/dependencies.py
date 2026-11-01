"""Dependencias de FastAPI (plan, estructura): SesionBd vive en db.sesion;
aquí entran `UsuarioActual` y `ProteccionCsrf`.

`UsuarioActual` verifica el access JWT Bearer, carga el usuario de
PostgreSQL, aplica la expiración por inactividad (AUT-08) y, si el usuario
tiene cambio obligatorio en TRUE, solo deja pasar `/auth/yo`,
`/auth/cambiar-password` y `/auth/logout` (403, `CAMBIO_PASSWORD_OBLIGATORIO`).
"""

import ipaddress
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, Request
from sqlalchemy import text

from app.config import obtener_settings
from app.core import seguridad, tiempo
from app.core.permisos import PERMISOS_POR_ROL
from app.db.sesion import SesionBd
from app.errors import ErrorDominio
from app.services import parametros

COOKIES_REFRESCO = "refresh_token"
COOKIES_CSRF = "csrf_token"

# Rutas declaradas en secciones 5.2; el resto queda restringido con cambio obligatorio.
RUTAS_CAMBIO_PERMITIDO = ("/auth/yo", "/auth/cambiar-password", "/auth/logout")


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Estado del usuario resuelto desde JWT + PostgreSQL."""

    id: int
    rol: str
    nombre: str
    correo: str
    debe_cambiar_password: bool
    familia_id: str | None
    id_sesion: int | None


def ip_valida(ip: str | None) -> str | None:
    """Solo deja pasar direcciones válidas para columnas `inet`."""
    if not ip:
        return None
    try:
        return ipaddress.ip_address(ip.strip()).compressed
    except ValueError:
        # El transporte ASGI de pruebas reporta clientes como `testclient`.
        return None


def ip_de_peticion(request: Request) -> str | None:
    cliente = request.client.host if request.client else None
    return ip_valida(cliente)


def user_agent_de_peticion(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def _usuario_de_peticion(request: Request, sesion: SesionBd) -> UsuarioAutenticado:
    """Resuelve el access JWT; 401 si falta, es inválido o la sesión murió."""
    cabecera = request.headers.get("authorization", "")
    if not cabecera.startswith("Bearer ") or cabecera.count(" ") != 1:
        raise ErrorDominio(401, "TOKEN_INVALIDO", "No hay sesión válida.")
    token = cabecera.partition(" ")[2].strip()
    try:
        claims = seguridad.decodificar_token(token)
    except seguridad.ErrorToken:
        raise ErrorDominio(
            401, "TOKEN_INVALIDO", "La sesión no es válida o está expirada."
        ) from None

    filas = await sesion.execute(
        text(
            """
            SELECT u.id, u.full_name, u.email, u.role, u.must_change_password,
                   r.id AS id_sesion, r.familia_id::text AS familia_id,
                   r.ultimo_uso_en, r.emitido_en, r.expira_en, r.revocado_en
            FROM app_users u
            JOIN refresh_tokens r ON r.id = CAST(:ses AS bigint) AND r.app_user_id = u.id
            WHERE u.id = CAST(:sub AS bigint)
            """
        ),
        {"sub": int(claims["sub"]), "ses": int(claims["ses"])},
    )
    fila = filas.mappings().first()
    if fila is None or fila["revocado_en"] is not None:
        raise ErrorDominio(401, "TOKEN_INVALIDO", "La sesión ya no existe.")

    inactividad_min = await parametros.numero(sesion, "sesion_inactividad_min")
    referencia = fila["ultimo_uso_en"] or fila["emitido_en"]
    expiro_por_inactividad = referencia is not None and (
        tiempo.ahora() >= referencia + timedelta(minutes=inactividad_min)
    )
    if fila["expira_en"] <= tiempo.ahora() or expiro_por_inactividad:
        raise ErrorDominio(
            401, "SESION_EXPIRADA", "La sesión expiró. Inicie sesión nuevamente."
        )

    # Un solo realce del seguimiento por access token emitido: si el token
    # es más nuevo que el último uso, la sesión avanza. En el resto de
    # peticiones la comparación descarta la escritura. PyJWT entrega `iat`
    # como epoch en segundos; la base compara timestamptz.
    instante_del_token = datetime.fromtimestamp(int(claims["iat"]), tz=UTC)
    await sesion.execute(
        text(
            """
            UPDATE refresh_tokens
            SET ultimo_uso_en = :ahora
            WHERE id = CAST(:ses AS bigint)
              AND (ultimo_uso_en IS NULL OR ultimo_uso_en < :iat)
            """
        ),
        {"ses": claims["ses"], "iat": instante_del_token, "ahora": tiempo.ahora()},
    )
    return UsuarioAutenticado(
        id=int(fila["id"]),
        rol=str(fila["role"]),
        nombre=str(fila["full_name"]),
        correo=str(fila["email"]),
        debe_cambiar_password=fila["must_change_password"] is True,
        familia_id=str(fila["familia_id"]),
        id_sesion=int(fila["id_sesion"]),
    )


async def usuario_actual(request: Request, sesion: SesionBd) -> UsuarioAutenticado:
    """Sin el puente de cambio obligatorio: para `/auth/yo`, cambiar y salir."""
    return await _usuario_de_peticion(request, sesion)


async def usuario_actual_autorizado(
    request: Request, sesion: SesionBd
) -> UsuarioAutenticado:
    """`UsuarioActual` del plan: aplica el cambio obligatorio salvo rutas de AUT-06."""
    usuario = await usuario_actual(request, sesion)
    if usuario.debe_cambiar_password:
        ruta = request.scope["path"].removeprefix(obtener_settings().api_v1_prefix)
        if ruta not in RUTAS_CAMBIO_PERMITIDO:
            raise ErrorDominio(
                403,
                "CAMBIO_PASSWORD_OBLIGATORIO",
                "Debe cambiar su contraseña antes de continuar.",
            )
    return usuario


def requiere_permiso(permiso: str) -> Callable:
    """Fase 3: exige que el rol del usuario registrado tenga el permiso.

    Se declara con `Depends(requiere_permiso("usuarios.gestionar"))`: además
    del permiso aplica todo `UsuarioActual` (cambio obligatorio incluido).
    """

    async def comprobado(
        # B008 intencional: es el patrón de dependencia anidada de FastAPI.
        usuario: UsuarioAutenticado = Depends(usuario_actual_autorizado),  # noqa: B008
    ) -> UsuarioAutenticado:
        if permiso not in PERMISOS_POR_ROL.get(usuario.rol, frozenset()):
            raise ErrorDominio(
                403,
                "SIN_PERMISO",
                "No tiene permiso para esta acción.",
                {"permiso": permiso},
            )
        return usuario

    return comprobado


async def proteccion_csrf(request: Request) -> None:
    """AUT-10/plan 4: valida CSRF cuando hay refresh-cookie (omitida vía Bearer).

    Un atacante sin el acceso a cookies del origen no puede responder ni con
    el origen ni con el token `csrf_token` (doble envío de cookie).
    """
    cookies_refresco = request.cookies.get(COOKIES_REFRESCO)
    if not cookies_refresco:
        return
    origen = request.headers.get("origin") or request.headers.get("referer")
    if origen:
        host = urlparse(origen).netloc
        if not host or host != (request.headers.get("host") or ""):
            raise ErrorDominio(403, "CSRF_INVALIDO", "Petición de otro origen.")
    token_header = request.headers.get("x-csrf-token")
    token_cookie = request.cookies.get(COOKIES_CSRF)
    if not token_header or token_header != token_cookie:
        raise ErrorDominio(
            403, "CSRF_INVALIDO", "Falta el token CSRF de la sesión de refresco."
        )
# Tipos `Annotated` listos para los endpoints, con los nombres del plan.
UsuarioActual = Annotated[UsuarioAutenticado, Depends(usuario_actual_autorizado)]
UsuarioActualSinCambios = Annotated[UsuarioAutenticado, Depends(usuario_actual)]

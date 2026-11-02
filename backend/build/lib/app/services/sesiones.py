"""Motor de sesiones del plan (Fase 2): intentos, familias de refresh y reCAPTCHA.

Todo vive sobre PostgreSQL (sin Redis): el límite de intentos consulta
`intentos_login` con los parámetros `login_intentos_max` y
`login_bloqueo_min`; los refresh tokens rotan dentro de una `familia_id`
guardada como hash. Cada endpoint del servicio commitea su transacción.
"""

import asyncio
import math
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import obtener_settings
from app.core import seguridad, tiempo
from app.services import auditoria, parametros

COOKIES_REFRESCO = "refresh_token"
COOKIES_CSRF = "csrf_token"

# Sin RECAPTCHA_SECRET_KEY (desarrollo/pruebas), el único modo de fallar la
# verificación es usar uno de estos valores de prueba; así la suite puede
# cubrir el rechazo sin red externa.
TOKENS_REGISTRADOS_FALLO = {"recaptcha_invalido", "recaptcha_score_bajo"}


@dataclass(frozen=True)
class SesionEmitida:
    """Una familia creada o renovada, lista para cookies y access JWT."""

    id_sesion: int
    familia_id: str
    token_refresco: str
    access_token: str
    segundos_access: int
    usuario_id: int
    nombre: str
    rol: str
    debe_cambiar_password: bool


def contextos_peticion(request: Request) -> tuple[str | None, str | None]:
    """IP y *user agent* de la petición, para `intentos_login` y `auditoria`."""
    cliente = request.client.host if request.client else None
    return auditoria.ip_valida(cliente), request.headers.get("user-agent")


def enlace_al_recuperar() -> str | None:
    """URL de la pantalla de restablecimiento, si la configuración la define."""
    ajustes = obtener_settings()
    base = ajustes.frontend_url.strip().rstrip("/")
    return f"{base}/restablecer" if base else None


async def verificar_recaptcha(token: str, hostname_peticion: str | None) -> bool:
    """AUT-01: valida la verificación v3 desde el backend, nunca en el cliente."""
    ajustes = obtener_settings()
    if not ajustes.recaptcha_secret_key:
        # Desarrollo/pruebas sin cuenta: falla solo si el uso envía un token
        # de fallo; cualquier otro token pasa como `texto_digital`.
        return bool(token) and token not in TOKENS_REGISTRADOS_FALLO
    cuerpo_verify = {
        "secret": ajustes.recaptcha_secret_key,
        "response": token,
    }
    try:
        # Cliente propio para no bloquear el hilo de eventos (ASYNC210).
        async with httpx.AsyncClient(timeout=10.0) as cliente:
            respuesta = await cliente.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data=cuerpo_verify,
            )
    except httpx.HTTPError:
        return False
    if respuesta.status_code != 200:
        return False
    datos = respuesta.json()
    if not datos.get("success"):
        return False
    umbral = ajustes.recaptcha_umbral_minimo
    if float(datos.get("score", 0.0)) < umbral:
        return False
    hostname_esperado = ajustes.recaptcha_hostname.strip() or (hostname_peticion or "")
    return datos.get("hostname", "") == hostname_esperado


async def minutos_bloqueo_restantes(sesion: AsyncSession, correo: str) -> int | None:
    """Minutos restantes de bloqueo, o `None` si puede intentar ahora.

    Cuenta los intentos fallidos consecutivos (desde el último exitoso)
    dentro de la ventana `login_bloqueo_min`; no siempre del correo viola
    `login_intentos_max`.
    """
    ventana = await parametros.numero(sesion, "login_bloqueo_min")
    maximo = await parametros.numero(sesion, "login_intentos_max")
    filas = await sesion.execute(
        text(
            """
            SELECT count(*) AS fallidos,
                   max(creado_en) AS ultimo_fallido
            FROM intentos_login
            WHERE lower(correo) = lower(:correo)
              AND NOT exitoso
              AND creado_en > now() - make_interval(mins => :ventana)
              AND creado_en > coalesce(
                    (SELECT max(creado_en)
                     FROM intentos_login
                     WHERE lower(correo) = lower(:correo)
                       AND exitoso),
                    '-infinity'::timestamptz
              )
            """
        ),
        {"correo": correo, "ventana": ventana},
    )
    fila = filas.mappings().one()
    if int(fila["fallidos"]) < maximo:
        return None
    ultimo = fila["ultimo_fallido"]
    restante_segundos = ventana * 60 - (
        tiempo.ahora() - ultimo.astimezone(tiempo.ZONA_LIMA)
    ).total_seconds()
    return max(1, math.ceil(restante_segundos / 60))


async def registrar_intento(
    sesion: AsyncSession,
    *,
    correo: str,
    ip: str | None,
    exitoso: bool,
    motivo: str | None = None,
) -> None:
    """Fila en `intentos_login` para el límite de intentos (AUT-04)."""
    await sesion.execute(
        text(
            """
            INSERT INTO intentos_login (correo, ip, exitoso, motivo)
            VALUES (:correo, CAST(:ip AS inet), :exitoso, :motivo)
            """
        ),
        {"correo": correo, "ip": ip, "exitoso": exitoso, "motivo": motivo},
    )


async def usuario_por_correo(sesion: AsyncSession, correo: str) -> Any:
    """Fila del usuario por correo (insensible a mayúsculas)."""
    filas = await sesion.execute(
        text(
            """
            SELECT id, full_name, email, role, password_hash, must_change_password
            FROM app_users
            WHERE lower(email) = lower(:correo)
            """
        ),
        {"correo": correo},
    )
    return filas.mappings().first()


async def emitir_sesion(
    sesion: AsyncSession,
    *,
    usuario_id: int,
    nombre: str,
    rol: str,
    debe_cambiar_password: bool,
    ip: str | None,
    user_agent: str | None,
    familia_id: str | None = None,
) -> SesionEmitida:
    """Crea una familia de refresh (login, rotación o cambio de contraseña).

    En la rotación (`rotar_refresh`) se conserva la familia del token usado:
    así, revocar la familia por reutilización alcanza a la sesión nueva.
    """
    ajustes = obtener_settings()
    dias = max(
        1,
        await parametros.numero(sesion, "refresh_token_dias"),
    )
    ahora = tiempo.ahora()
    mismo_token = seguridad.generar_token_opaco()
    familia = familia_id or str(uuid.uuid4())
    filas = await sesion.execute(
        text(
            """
            INSERT INTO refresh_tokens
                (app_user_id, familia_id, token_hash, emitido_en, expira_en,
                 ultimo_uso_en, ip, user_agent)
            VALUES (:usuario_id, CAST(:familia AS uuid), :hash, :ahora, :expira,
                    :ahora, CAST(:ip AS inet), :user_agent)
            RETURNING id
            """
        ),
        {
            "usuario_id": usuario_id,
            "familia": familia,
            "hash": seguridad.hash_opaco(mismo_token),
            "ahora": ahora,
            "expira": ahora + timedelta(days=dias),
            "ip": ip,
            "user_agent": user_agent,
        },
    )
    id_sesion = int(filas.scalar_one())
    return SesionEmitida(
        id_sesion=id_sesion,
        familia_id=familia,
        token_refresco=mismo_token,
        access_token=seguridad.crear_token_acceso(
            usuario_id, rol, id_sesion, debe_cambiar_password
        ),
        segundos_access=ajustes.access_token_minutos * 60,
        usuario_id=usuario_id,
        nombre=nombre,
        rol=rol,
        debe_cambiar_password=debe_cambiar_password,
    )


async def rotar_refresh(
    sesion: AsyncSession, *, token_actual: str, ip: str | None, user_agent: str | None
) -> SesionEmitida | None:
    """AUT-10: invalida el token usado y entrega uno nuevo de la misma familia.

    Devuelve `None` si el token no existe, está revocado o expiró.
    """
    filas = await sesion.execute(
        text(
            """
            SELECT r.id, r.app_user_id, r.familia_id::text, r.expira_en, r.revocado_en,
                   u.role, u.full_name, u.must_change_password
            FROM refresh_tokens r
            JOIN app_users u ON u.id = r.app_user_id
            WHERE r.token_hash = :hash
            """
        ),
        {"hash": seguridad.hash_opaco(token_actual)},
    )
    fila = filas.mappings().first()
    if fila is None:
        return None

    # Reutilización: la familia entera se considera comprometida (AUT-10).
    if fila["revocado_en"] is not None:
        await revocar_familia(sesion, familia_id=str(fila["familia_id"]))
        return None
    # La fila trae timestamptz desde asyncpg; comparar instantes directos.
    if fila["expira_en"] <= tiempo.ahora():
        return None
    nueva = await emitir_sesion(
        sesion,
        usuario_id=int(fila["app_user_id"]),
        nombre=str(fila["full_name"]),
        rol=str(fila["role"]),
        debe_cambiar_password=bool(fila["must_change_password"]),
        ip=ip,
        user_agent=user_agent,
        familia_id=str(fila["familia_id"]),
    )
    await sesion.execute(
        text(
            """
            UPDATE refresh_tokens
            SET revocado_en = :ahora, reemplazado_por_id = :nueva
            WHERE id = :antigua
            """
        ),
        {"ahora": tiempo.ahora(), "nueva": nueva.id_sesion, "antigua": int(fila["id"])},
    )
    return nueva


async def revocar_familia(sesion: AsyncSession, *, familia_id: str) -> None:
    """Revoca la familia entera (logout, cambio de contraseña, reutilización)."""
    await sesion.execute(
        text(
            """
            UPDATE refresh_tokens
            SET revocado_en = :ahora
            WHERE familia_id = CAST(:familia AS uuid)
              AND revocado_en IS NULL
            """
        ),
        {"familia": familia_id, "ahora": tiempo.ahora()},
    )


async def revocar_todas(sesion: AsyncSession, *, usuario_id: int) -> None:
    """Revoca todas las familias activas de un usuario (restablecimiento)."""
    await sesion.execute(
        text(
            """
            UPDATE refresh_tokens
            SET revocado_en = :ahora
            WHERE app_user_id = :usuario_id
              AND revocado_en IS NULL
            """
        ),
        {"usuario_id": usuario_id, "ahora": tiempo.ahora()},
    )


async def actualizar_acceso(
    sesion: AsyncSession, *, usuario_id: int, id_sesion: int | None
) -> None:
    """Marca actividad: `ultimo_acceso_en` del usuario y `ultimo_uso_en` de la sesión."""
    await sesion.execute(
        text("UPDATE app_users SET ultimo_acceso_en = :ahora WHERE id = :usuario_id"),
        {"usuario_id": usuario_id, "ahora": tiempo.ahora()},
    )
    await sesion.execute(
        text(
            """
            UPDATE refresh_tokens
            SET ultimo_uso_en = :ahora
            WHERE id = :id_sesion
            """
        ),
        {"id_sesion": id_sesion, "ahora": tiempo.ahora()},
    )


async def verificar_password(
    texto: str, hash_almacenado: str
) -> bool:
    """El hashing es CPU-bound: sale del hilo de eventos."""
    return await asyncio.to_thread(seguridad.verificar_password, texto, hash_almacenado)


async def registrar_login_en_auditoria(
    sesion: AsyncSession,
    *,
    usuario_id: int | None,
    accion: str,
    correo: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Fila de auditoría del intento (AUD-01), controlado por el llamador."""
    await auditoria.registrar(
        sesion,
        usuario_id=usuario_id,
        accion=accion,
        entidad="app_user",
        entidad_id=usuario_id,
        despues={"correo": correo},
        ip=ip,
        user_agent=user_agent,
    )

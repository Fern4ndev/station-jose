"""Primitivas de seguridad del plan (Fase 2): contraseñas, JWT y tokens opacos.

- Contraseñas siempre con Argon2id (`pwdlib`), nunca en texto plano.
- Access JWT firmado con PyJWT, de vida corta y claims mínimos.
- Refresh tokens aleatorios opacos: se guardan solo como hash SHA-256
  (64 caracteres hexadecimales, como exige la migración 0001).
- Tokens CSRF aleatorios para la doble verificación de cookie.

Los secretos viven en la configuración protegida del servidor (`.env`),
jamás en el código ni en los logs.
"""

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config import obtener_settings

_gestor = PasswordHash.recommended()

ALGORITMO_JWT = "HS256"


class ErrorToken(Exception):
    """El access JWT no es válido, expiró o le faltan claims."""


def hashear_password(contrasena: str) -> str:
    """Contraseña → hash Argon2id con sal."""
    return _gestor.hash(contrasena)


def verificar_password(contrasena: str, hash_almacenado: str) -> bool:
    """Comparación segura en tiempo constante; nunca revela el hash."""
    try:
        return _gestor.verify(contrasena, hash_almacenado)
    except Exception:  # pwdlib: hash corrupto o formato desconocido
        return False


# Caracteres sin ambigüedad (sin 0/O, 1/l/I) para una contraseña temporal que
# se escribe a mano desde la impresión de `crear-admin`.
_ALFABETO_TEMPORAL = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
_DIGITOS_TEMPORALES = "23456789"


def generar_password_temporal(largo: int = 12) -> str:
    """Contraseña temporal con mayúscula, minúscula y dígito garantizados."""
    secreto = [
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"),
        secrets.choice("abcdefghijkmnopqrstuvwxyz"),
        secrets.choice(_DIGITOS_TEMPORALES),
    ]
    secreto.extend(secrets.choice(_ALFABETO_TEMPORAL) for _ in range(largo - len(secreto)))
    secrets.SystemRandom().shuffle(secreto)
    return "".join(secreto)


def generar_token_opaco() -> str:
    """Refresh token aleatorio de 64 caracteres para la cookie."""
    return secrets.token_urlsafe(48)


def generar_token_csrf() -> str:
    """Token CSRF aleatorio para la cookie no HttpOnly."""
    return secrets.token_urlsafe(32)


def hash_opaco(token: str) -> str:
    """En `refresh_tokens`/`tokens_recuperacion` solo viaja el hash SHA-256."""
    return sha256(token.encode("utf-8")).hexdigest()


def crear_token_acceso(
    usuario_id: int, rol: str, id_sesion: int, debe_cambiar_password: bool
) -> str:
    """Access JWT de vida corta con claims mínimos (plan, sección 4).

    `sub` es el id del usuario, `rol` su rol, `ses` la sesión de refresh que
    respalda el token y `cambio` el indicador de cambio obligatorio.
    """
    ajustes = obtener_settings()
    instante = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol,
        "ses": id_sesion,
        "cambio": bool(debe_cambiar_password),
        "iat": instante,
        "exp": instante + timedelta(minutes=ajustes.access_token_minutos),
    }
    return jwt.encode(claims, ajustes.jwt_secret_key, algorithm=ALGORITMO_JWT)


def decodificar_token(token: str) -> dict[str, Any]:
    """Verifica firma y expiración; devuelve los claims o lanza `ErrorToken`."""
    ajustes = obtener_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            ajustes.jwt_secret_key,
            algorithms=[ALGORITMO_JWT],
            options={"require": ["sub", "rol", "ses", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ErrorToken("El token expiró.") from exc
    except jwt.InvalidTokenError as exc:
        raise ErrorToken("El token no es válido.") from exc
    if (
        not isinstance(claims["ses"], int)
        or not isinstance(claims["rol"], str)
        or not isinstance(claims["sub"], str)
        or not claims["sub"].isdigit()
    ):
        raise ErrorToken("Los claims del token están incompletos.")
    return claims

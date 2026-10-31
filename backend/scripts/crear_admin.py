"""Crea el administrador inicial de la base de datos.

Provisional hasta que exista `python -m app.cli` (fase 2 del plan). Crea un
registro en `app_users` con rol `administrador` y contraseña cifrada con Argon2.

Uso, desde `backend/` con el entorno virtual activo:

    python scripts/crear_admin.py admin@ejemplo.pe
    python scripts/crear_admin.py admin@ejemplo.pe --url postgresql://...

La contraseña se pide por consola y nunca se guarda en texto plano.
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def leer_argumentos() -> argparse.Namespace:
    analizador = argparse.ArgumentParser(description="Crea el administrador inicial.")
    analizador.add_argument("correo", help="Correo del administrador.")
    analizador.add_argument(
        "--nombre",
        default="Administrador",
        help="Nombre visible (por defecto: Administrador).",
    )
    analizador.add_argument(
        "--url",
        default=None,
        help="Cadena de conexión. Por defecto usa MIGRADOR_URL del .env.",
    )
    return analizador.parse_args()


async def crear_admin(correo: str, nombre: str, url: str, clave: str) -> int:
    import asyncpg
    from pwdlib import PasswordHash

    hash_clave = PasswordHash.recommended().hash(clave)
    conexion = await asyncpg.connect(url)
    try:
        fila = await conexion.fetchrow(
            """
            INSERT INTO app_users (full_name, email, password_hash, role, must_change_password)
            VALUES ($1, $2, $3, 'administrador', TRUE)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            nombre,
            correo,
            hash_clave,
        )
    finally:
        await conexion.close()

    if fila is None:
        print(f"Ya existe un usuario con el correo {correo}.")
        return 1

    print(f"Administrador creado con id {fila['id']} ({correo}).")
    return 0


def main() -> int:
    from app.config import obtener_settings

    argumentos = leer_argumentos()
    url = argumentos.url or obtener_settings().migrador_url
    if not url:
        print("Falta la cadena de conexión: usa --url o define MIGRADOR_URL.")
        return 2

    correo = argumentos.correo.strip().lower()
    clave = getpass.getpass("Contraseña del administrador: ")
    if len(clave) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return 2
    if clave != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        return 2

    return asyncio.run(crear_admin(correo, argumentos.nombre, url, clave))


if __name__ == "__main__":
    raise SystemExit(main())

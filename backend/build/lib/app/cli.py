"""CLI del backend: `python -m app.cli <comando>`.

Comandos disponibles en la Fase 2:
- `migrar estado`            lista migraciones aplicadas y pendientes.
- `migrar aplicar [--test]`  aplica las pendientes sobre la base del entorno.
- `migrar nueva <nombre>`    genera el siguiente archivo `NNNN_<slug>.sql`.
- `crear-admin --nombre ... --correo ... [--test]`
                             crea el administrador con una contraseña temporal
                             que se imprime una sola vez y exige el cambio
                             (must_change_password TRUE).

Las conexiones de migración salen de `backend/.env` (`MIGRADOR_URL`); con
`--test` se usa `MIGRADOR_URL_TEST` para la base de pruebas.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from contextlib import suppress

import asyncpg

from app.config import obtener_settings
from app.core import seguridad
from app.db import migrar


def url_migrador(usar_pruebas: bool) -> str:
    """URL del rol dueño del esquema; con --test, la de la base de pruebas."""
    ajustes = obtener_settings()
    if usar_pruebas:
        return ajustes.migrador_url_test or ajustes.migrador_url
    return ajustes.migrador_url


def preparar_salida() -> None:
    """Permite imprimir marcas como ✓ en consolas Windows heredadas (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            with suppress(OSError, ValueError):  # flujo no reconfigurable
                flujo.reconfigure(encoding="utf-8", errors="replace")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description="CLI del backend San José.")
    comandos = parser.add_subparsers(dest="comando", required=True)

    migrar_parser = comandos.add_parser("migrar", help="migraciones SQL numeradas")
    migrar_parser.add_argument("accion", choices=["estado", "aplicar", "nueva"])
    migrar_parser.add_argument("nombre", nargs="?", help="nombre de la migración (solo con nueva)")
    migrar_parser.add_argument(
        "--test", action="store_true", help="opera sobre la base de pruebas"
    )

    admin_parser = comandos.add_parser(
        "crear-admin", help="crea el administrador inicial con contraseña temporal"
    )
    admin_parser.add_argument(
        "--nombre", required=True, help="nombre visible del administrador"
    )
    admin_parser.add_argument("--correo", required=True, help="correo de acceso (único)")
    admin_parser.add_argument(
        "--test", action="store_true", help="crea el usuario en la base de pruebas"
    )
    return parser


async def ejecutar_migrar(accion: str, nombre: str | None, usar_pruebas: bool) -> int:
    try:
        if accion == "nueva":
            if not nombre:
                print("El comando `migrar nueva` requiere un nombre.", file=sys.stderr)
                return 2
            ruta = migrar.nueva(nombre)
            print(f"✓ Creado {ruta} ({ruta.relative_to(migrar.DIRECTORIO_MIGRACIONES.parent)}).")
            return 0

        url = url_migrador(usar_pruebas)
        if accion == "estado":
            imagen = await migrar.estado(url)
            if imagen.aplicadas:
                print("Aplicadas:")
                for version, nombre_archivo in imagen.aplicadas:
                    print(f"  ✓ {version}_{nombre_archivo}")
            else:
                print("No hay migraciones registradas todavía.")
            if imagen.pendientes:
                print("Pendientes:")
                for version, nombre_archivo in imagen.pendientes:
                    print(f"  · {version}_{nombre_archivo}")
            else:
                print("Sin migraciones pendientes.")
            return 0

        aplicadas = await migrar.aplicar(url)
        print(f"Migraciones aplicadas: {len(aplicadas)}.")
        return 0
    except migrar.ErrorMigracion as exc:
        print(f"FALLA: {exc}", file=sys.stderr)
        return 1


async def ejecutar_crear_admin(nombre: str, correo: str, usar_pruebas: bool) -> int:
    """Crea el administrador con contraseña temporal impresa una sola vez.

    `must_change_password` queda en TRUE: en el primer inicio de sesión el
    sistema exige el cambio (AUT-06) y restringe el resto de la API.
    """
    url = url_migrador(usar_pruebas)
    if not url:
        print(
            "Falta MIGRADOR_URL en backend/.env: el comando conecta con el rol "
            "dueño del esquema para evitar problemas de permisos.",
            file=sys.stderr,
        )
        return 2

    correo_normalizado = correo.strip().lower()
    clave_temporal = seguridad.generar_password_temporal()
    # Argon2 es CPU-bound: se computa fuera del hilo de eventos.
    hash_clave = await asyncio.to_thread(seguridad.hashear_password, clave_temporal)

    try:
        conexion = await asyncpg.connect(migrar.a_dsn(url))
    except asyncpg.PostgresError as exc:
        print(f"FALLA: no se pudo conectar con {migrar.a_dsn(url)}: {exc}", file=sys.stderr)
        return 1
    try:
        fila = await conexion.fetchrow(
            """
            INSERT INTO app_users
                (full_name, email, password_hash, role, must_change_password)
            VALUES ($1, $2, $3, 'administrador', TRUE)
            RETURNING id
            """,
            nombre.strip(),
            correo_normalizado,
            hash_clave,
        )
    except asyncpg.UniqueViolationError:
        print(f"Ya existe un usuario con el correo {correo_normalizado}.", file=sys.stderr)
        return 1
    finally:
        await conexion.close()

    if fila is None:
        print("No se pudo crear el administrador.", file=sys.stderr)
        return 1

    print(f"✓ Administrador creado: id {fila['id']} ({correo_normalizado}).")
    print("\nContraseña temporal (no se volverá a mostrar, sostenerla con cuidado):")
    print(f"    {clave_temporal}\n")
    print("En el primer inicio de sesión el sistema exigirá cambiarla.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    preparar_salida()
    args = construir_parser().parse_args(argv)
    if args.comando == "migrar":
        return asyncio.run(ejecutar_migrar(args.accion, args.nombre, args.test))
    if args.comando == "crear-admin":
        return asyncio.run(ejecutar_crear_admin(args.nombre, args.correo, args.test))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

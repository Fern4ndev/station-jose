"""CLI del backend: `python -m app.cli <comando>`.

Comandos disponibles en la Fase 1:
- `migrar estado`            lista migraciones aplicadas y pendientes.
- `migrar aplicar [--test]`  aplica las pendientes sobre la base del entorno.
- `migrar nueva <nombre>`    genera el siguiente archivo `NNNN_<slug>.sql`.

Las conexiones salen de `backend/.env` (`MIGRADOR_URL`); con `--test` se usa
`MIGRADOR_URL_TEST` para la base de pruebas.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from contextlib import suppress

from app.config import obtener_settings
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


def main(argv: Sequence[str] | None = None) -> int:
    preparar_salida()
    args = construir_parser().parse_args(argv)
    if args.comando == "migrar":
        return asyncio.run(ejecutar_migrar(args.accion, args.nombre, args.test))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

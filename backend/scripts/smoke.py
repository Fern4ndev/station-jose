"""Recorrido de verificación por fase: `python scripts/smoke.py --hasta N`.

Es acumulativo: cada fase agrega comprobaciones numeradas y al ejecutar con
`--hasta N` se repiten todas las de las fases anteriores. Salida `OK` o
`FALLA` por comprobación; el proceso termina con código 1 si alguna falla.
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TypedDict

import httpx

COMPROBACION = Callable[[httpx.AsyncClient], Awaitable[str | None]]
"""Devuelve None si la comprobación pasa; una explicación si falla."""


class Fase(TypedDict):
    numero: int
    titulo: str
    comprobaciones: tuple[tuple[str, COMPROBACION], ...]


async def _salud_en_ok(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.get("/api/v1/salud")
    if respuesta.status_code != 200:
        return f"GET /api/v1/salud devolvió {respuesta.status_code}."
    datos = respuesta.json()
    if datos.get("estado") != "ok":
        return f"El estado no es 'ok': {datos}"
    return None


async def _enums_completos(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.get("/api/v1/catalogos/enums")
    if respuesta.status_code != 200:
        return f"GET /api/v1/catalogos/enums devolvió {respuesta.status_code}."
    datos = respuesta.json()
    faltan = [
        clave
        for clave in ("roles", "estados_orden", "estados_vale", "tipos_movimiento", "permisos")
        if clave not in datos
    ]
    if faltan:
        return f"Faltan claves en la respuesta: {', '.join(faltan)}."
    return None


async def _openapi_generado(cliente: httpx.AsyncClient) -> str | None:
    respuesta = await cliente.get("/openapi.json")
    if respuesta.status_code != 200:
        return "La documentación OpenAPI no está disponible (¿estás en desarrollo?)."
    return None


FASES: tuple[Fase, ...] = (
    {
        "numero": 1,
        "titulo": "Esqueleto FastAPI, PostgreSQL y migraciones propias",
        "comprobaciones": (
            ("001 salud con PostgreSQL y OCR en ok", _salud_en_ok),
            ("002 catálogos de enums completos", _enums_completos),
            ("003 documentación OpenAPI generada", _openapi_generado),
        ),
    },
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="origen de la API")
    parser.add_argument("--hasta", type=int, default=1, help="última fase a comprobar")
    parser.add_argument("--segundos", type=float, default=10.0, help="segundos por petición")
    return parser


def _fases_hasta(limite: int) -> tuple[Fase, ...]:
    fases = tuple(fase for fase in FASES if fase["numero"] <= limite)
    if limite > FASES[-1]["numero"]:
        print(
            f"Aviso: la fase {limite} aún no tiene comprobaciones; máximo {FASES[-1]['numero']}.",
            file=sys.stderr,
        )
    return fases


async def recorrer(url: str, limite: int, segundos: float) -> int:
    fallas = 0
    limite_util = max(1, limite)
    async with httpx.AsyncClient(base_url=url, timeout=segundos) as cliente:
        for fase in _fases_hasta(limite_util):
            print(f"\nFase {fase['numero']}: {fase['titulo']}")
            for titulo, comprobar in fase["comprobaciones"]:
                try:
                    detalle = await comprobar(cliente)
                except httpx.HTTPError as exc:
                    detalle = f"No se pudo conectar: {exc}"
                if detalle is None:
                    print(f"  OK    {titulo}")
                else:
                    fallas += 1
                    print(f"  FALLA {titulo}: {detalle}")
    return 1 if fallas else 0


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            with suppress(OSError, ValueError):  # flujo no reconfigurable
                flujo.reconfigure(encoding="utf-8", errors="replace")
    argumentos = construir_parser().parse_args()
    print(f"Recorrido smoke contra {argumentos.url} hasta la fase {argumentos.hasta}.")
    codigo = asyncio.run(recorrer(argumentos.url, argumentos.hasta, argumentos.segundos))
    if codigo == 0:
        print("\nRecorrido terminado en verde.")
    else:
        print("\nRecorrido con fallas.", file=sys.stderr)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())

"""Divide la verdad terreno en grupos de desarrollo y prueba (Fase 10).

Recorre `datos/verdad_terreno/`, respeta la proporcion del plan (aprox. 70 %
desarrollo, 30 % prueba) estratificada por categoria (digital, escaneo, foto)
y escribe `datos/division.json` con un `seed` fijo: la misma carpeta siempre
produce la misma division, asi los ajustes de una corrida se comparan con la
otra sin mezclar grupos.

La division NO se rehace a mano cuando cambian los documentos: se vuelve a
correr este script y los informes antiguos quedan fechados en `informes/`.

Uso:

    python scripts/dividir_dataset.py
    python scripts/dividir_dataset.py --desarrollo 0.7 --seed 2026
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERDAD_POR_DEFECTO = RAIZ / "datos" / "verdad_terreno"
DIVISION_POR_DEFECTO = RAIZ / "datos" / "division.json"
CATEGORIAS = ("digital", "escaneo", "foto")


def dividir(
    por_carpeta: dict[str, list[str]], semilla: int, fraccion: float
) -> dict[str, list[str]]:
    """Parte cada categoría determinísticamente con `random.Random(semilla)`.

    La prueba recibe al menos un documento en cuanto la categoría tiene
    tres, para que la evaluación final siempre tenga con qué medir.
    """
    # La semilla pseudo-aleatoria es el punto: reproducible, no criptográfica.
    azar = random.Random(semilla)  # noqa: S311
    grupos = {"desarrollo": [], "prueba": []}
    for categoria in CATEGORIAS:
        nombres = sorted(por_carpeta.get(categoria, []))
        azar.shuffle(nombres)
        de_prueba = round(len(nombres) * (1.0 - fraccion))
        if len(nombres) >= 3 and de_prueba == 0:
            de_prueba = 1
        grupos["prueba"].extend(nombres[:de_prueba])
        grupos["desarrollo"].extend(nombres[de_prueba:])
    grupos["desarrollo"].sort()
    grupos["prueba"].sort()
    return grupos


def cargar_por_carpeta(carpeta: Path) -> dict[str, list[str]]:
    """Lee cada verdad terreno y agrupa sus nombres de archivo por categoría."""
    por_categoria: dict[str, list[str]] = {}
    rutas = sorted(carpeta.glob("*.json"))
    if not rutas:
        print(f"No hay verdades terreno (JSON) en {carpeta}.", file=sys.stderr)
        print(
            "Crea un JSON por documento con las claves 'archivo', "
            "'categoria' y 'campos' (ver datos/README.md).",
            file=sys.stderr,
        )
        raise SystemExit(2)
    for ruta in rutas:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        categoria = contenido.get("categoria")
        if categoria not in CATEGORIAS:
            print(
                f"{ruta.name}: categoria invalida '{categoria}' "
                f"(usa una de: {', '.join(CATEGORIAS)}).",
                file=sys.stderr,
            )
            raise SystemExit(2)
        archivo = contenido.get("archivo") or ruta.stem
        por_categoria.setdefault(categoria, []).append(archivo)
        ruta_documento = RAIZ / "datos" / "documentos" / archivo
        if not ruta_documento.is_file():
            print(
                f"Aviso: el documento '{archivo}' aun no esta en datos/documentos/.",
                file=sys.stderr,
            )
    return por_categoria


def guardar_division(
    ruta: Path, grupos: dict[str, list[str]], semilla: int, fraccion: float
) -> None:
    """Escribe division.json con fecha, seed y fracción usadas."""
    division = {
        "creado": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": semilla,
        "fraccion_desarrollo": fraccion,
        "desarrollo": grupos["desarrollo"],
        "prueba": grupos["prueba"],
    }
    ruta.write_text(
        json.dumps(division, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del comando; devuelve el código de salida del proceso."""
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--verdad", type=Path, default=VERDAD_POR_DEFECTO)
    argumentos.add_argument("--division", type=Path, default=DIVISION_POR_DEFECTO)
    argumentos.add_argument("--desarrollo", type=float, default=0.7)
    argumentos.add_argument("--seed", type=int, default=2026)
    opciones = argumentos.parse_args(argv)

    por_carpeta = cargar_por_carpeta(opciones.verdad)
    grupos = dividir(
        por_carpeta, opciones.seed, min(0.9, max(0.1, opciones.desarrollo))
    )
    guardar_division(opciones.division, grupos, opciones.seed, opciones.desarrollo)
    total = sum(len(nombres) for nombres in por_carpeta.values())
    print(
        f"division.json: {len(grupos['desarrollo'])} de desarrollo y "
        f"{len(grupos['prueba'])} de prueba ({total} documentos)."
    )
    print("El grupo de prueba no se toca hasta la evaluacion final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

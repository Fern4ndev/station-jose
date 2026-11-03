"""Prepara 30 órdenes escaneadas para revisión manual de verdad terreno.

Los campos de entrada salen de la extracción OCR anterior y quedan marcados
como borradores; el evaluador no los acepta hasta la validación humana.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "datos" / "resultados_ordenes" / "ordenes_extraidas.json"
ORIGEN_DEFECTO = Path.home() / "Downloads" / "ordenes"
DOCUMENTOS = RAIZ / "datos" / "documentos"
VERDADES = RAIZ / "datos" / "verdad_terreno"


def elegibles(registros: list[dict]) -> list[dict]:
    """Filtra órdenes con los datos mínimos para una verdad terreno revisable."""
    salida = []
    for registro in registros:
        campos = registro["campos"]
        proveedor = campos.get("proveedor") or {}
        requerido = (
            campos.get("numero_orden"),
            campos.get("numero_siaf"),
            campos.get("fecha"),
            campos.get("unidad_ejecutora"),
            campos.get("ruc_unidad_ejecutora"),
            proveedor.get("razon_social"),
            proveedor.get("ruc"),
            campos.get("sede_estacion"),
            campos.get("partidas_combustible"),
        )
        if all(requerido) and not campos.get("partidas_pendientes_revision"):
            salida.append(registro)
    return salida


def seleccionar(registros: list[dict], cantidad: int) -> list[dict]:
    """Elige de forma estable priorizando entidades y sedes distintas."""
    disponibles = sorted(
        elegibles(registros),
        key=lambda item: (
            bool(item["campos"].get("fecha_correccion_ocr")),
            -len(item["campos"].get("partidas_combustible", [])),
            item["archivo"].casefold(),
        ),
    )
    elegidas: list[dict] = []
    conteo_entidad: Counter[str] = Counter()
    sedes: set[str] = set()
    while disponibles and len(elegidas) < cantidad:

        def puntuacion(item: dict) -> tuple[int, int, int, str]:
            campos = item["campos"]
            entidad = campos.get("unidad_ejecutora") or ""
            sede = campos.get("sede_estacion") or ""
            return (
                int(sede not in sedes) * 30,
                int(conteo_entidad[entidad] == 0) * 20 - max(0, conteo_entidad[entidad] - 1) * 5,
                len(campos.get("partidas_combustible", [])),
                item["archivo"].casefold(),
            )

        elegido = max(disponibles, key=puntuacion)
        disponibles.remove(elegido)
        elegidas.append(elegido)
        conteo_entidad[elegido["campos"].get("unidad_ejecutora") or ""] += 1
        sedes.add(elegido["campos"].get("sede_estacion") or "")
    if len(elegidas) < cantidad:
        raise ValueError(f"Solo hay {len(elegidas)} órdenes elegibles; se requieren {cantidad}.")
    return sorted(elegidas, key=lambda item: item["archivo"].casefold())


def verdad_borrador(registro: dict) -> dict:
    campos = registro["campos"]
    proveedor = campos["proveedor"]
    monto = sum(
        (Decimal(fila["precio_total"]) for fila in campos["partidas_combustible"]),
        start=Decimal("0"),
    ).quantize(Decimal("0.01"))
    partidas = [
        {
            "cantidad": fila["cantidad"],
            "unidad_medida": fila["unidad_medida"],
            "descripcion": fila["descripcion"],
            "precio_unitario": fila["precio_unitario"],
            "precio_total": fila["precio_total"],
        }
        for fila in campos["partidas_combustible"]
    ]
    return {
        "archivo": registro["archivo"],
        "categoria": "escaneo",
        "campos": {
            "numero_orden": campos["numero_orden"],
            "fecha": campos["fecha"],
            "monto": f"{monto:.2f}",
            "institucion": proveedor["razon_social"],
        },
        "datos_orden": {
            "numero_siaf": campos["numero_siaf"],
            "proveedor": {
                "razon_social": proveedor["razon_social"],
                "ruc": proveedor["ruc"],
                "direccion": proveedor.get("direccion"),
            },
            "sede_estacion": campos["sede_estacion"],
            "unidad_ejecutora": campos["unidad_ejecutora"],
            "codigo_unidad_ejecutora": campos.get("codigo_unidad_ejecutora"),
            "ruc_unidad_ejecutora": campos["ruc_unidad_ejecutora"],
            "partidas_combustible": partidas,
        },
        "borrador_generado_por_ocr": True,
        "revisada_dos_pasadas": False,
        "estado_revision": "pendiente_revision_usuario",
        "evidencia_ocr": registro["texto_ocr"],
        "notas": (
            "Revisar cada campo contra el PDF. El monto es la suma OCR de las "
            "partidas aceptadas. Corregir errores y marcar revisada_dos_pasadas "
            "como true solo después del cotejo manual."
        ),
    }


def preparar(origen: Path, cantidad: int) -> tuple[int, int]:
    registros = json.loads(RESULTADOS.read_text(encoding="utf-8"))
    elegidas = seleccionar(registros, cantidad)
    DOCUMENTOS.mkdir(parents=True, exist_ok=True)
    VERDADES.mkdir(parents=True, exist_ok=True)

    # Solo estos 30 documentos forman el conjunto de Fase 10.
    for carpeta in (DOCUMENTOS, VERDADES):
        for ruta in carpeta.iterdir():
            if ruta.is_file() and ruta.name != ".gitkeep":
                ruta.unlink()

    filas_revision = []
    for registro in elegidas:
        nombre = registro["archivo"]
        fuente = origen / nombre
        if not fuente.is_file():
            raise FileNotFoundError(f"No se encontró el PDF fuente: {fuente}")
        shutil.copy2(fuente, DOCUMENTOS / nombre)
        verdad = verdad_borrador(registro)
        ruta_verdad = VERDADES / f"{nombre}.json"
        ruta_verdad.write_text(
            json.dumps(verdad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        d = verdad["datos_orden"]
        filas_revision.append(
            {
                "archivo": nombre,
                "numero_orden": verdad["campos"]["numero_orden"],
                "numero_siaf": d["numero_siaf"],
                "fecha_dd_mm_aaaa": "/".join(reversed(verdad["campos"]["fecha"].split("-"))),
                "monto_soles": verdad["campos"]["monto"],
                "proveedor": d["proveedor"]["razon_social"],
                "ruc_proveedor": d["proveedor"]["ruc"],
                "direccion_proveedor": d["proveedor"].get("direccion") or "",
                "sede": d["sede_estacion"],
                "unidad_ejecutora": d["unidad_ejecutora"],
                "ruc_unidad_ejecutora": d["ruc_unidad_ejecutora"],
                "partidas_json": json.dumps(d["partidas_combustible"], ensure_ascii=False),
                "evidencia_ocr": " | ".join(
                    linea.strip()
                    for linea in registro["texto_ocr"].splitlines()
                    if any(
                        marca.casefold() in linea.casefold()
                        for marca in (
                            "ORDEN DE COMPRA",
                            "SIAF",
                            "UNIDAD EJECUTORA",
                            "Señor",
                            "RUC",
                            "Facturar",
                            "172100",
                        )
                    )
                ),
                "revisada": "",
                "correcciones_usuario": "",
            }
        )

    csv_path = RAIZ / "datos" / "revision_verdad_terreno.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as salida:
        writer = csv.DictWriter(salida, fieldnames=list(filas_revision[0]))
        writer.writeheader()
        writer.writerows(filas_revision)

    manifest = {
        "total": cantidad,
        "origen": str(origen),
        "archivos": [item["archivo"] for item in elegidas],
        "estado": "pendiente_revision_usuario",
        "division": {"desarrollo": 21, "prueba": 9},
        "criterio": (
            "prioriza campos completos, partidas consistentes, entidades y " "sedes distintas"
        ),
    }
    (RAIZ / "datos" / "seleccion_fase10.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(elegidas), sum(len(item["campos"]["partidas_combustible"]) for item in elegidas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", type=Path, default=ORIGEN_DEFECTO)
    parser.add_argument("--cantidad", type=int, default=30)
    args = parser.parse_args()
    ordenes, partidas = preparar(args.origen, args.cantidad)
    print(f"Preparadas {ordenes} órdenes y {partidas} partidas para revisión humana.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

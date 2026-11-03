"""Importa una muestra local de órdenes y prepara verdades para revisión.

Los documentos se mantienen fuera de Git. Las extracciones iniciales son
borradores, nunca verdad terreno confirmada: requieren revisión visual.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def importar(origen: Path, limite: int, documentos: Path, verdades: Path) -> int:
    from app.services.ocr.pipeline import procesar

    documentos.mkdir(parents=True, exist_ok=True)
    verdades.mkdir(parents=True, exist_ok=True)
    total = 0
    huellas: set[str] = set()
    for fuente in sorted(origen.glob("*.pdf")):
        huella = hashlib.sha256(fuente.read_bytes()).hexdigest()
        if huella in huellas:
            continue
        huellas.add(huella)
        if total >= limite:
            break
        destino = documentos / fuente.name
        ruta_verdad = verdades / f"{fuente.name}.json"
        if not destino.exists():
            shutil.copy2(fuente, destino)
        if ruta_verdad.exists():
            total += 1
            continue
        resultado = procesar(destino.read_bytes())
        campos = {campo.clave: campo.valor for campo in resultado.campos}
        verdad = {
            "archivo": fuente.name,
            "categoria": "digital" if resultado.metodo == "texto_digital" else "escaneo",
            "campos": campos,
            "datos_orden": {
                "numero_siaf": None,
                "proveedor": {"razon_social": None, "ruc": None},
                "sede": None,
                "unidad_ejecutora": None,
                "ruc_unidad_ejecutora": None,
                "partidas": [],
            },
            "borrador_generado_por_ocr": True,
            "revisada_dos_pasadas": False,
            "notas": (
                "Verificar visualmente cada dato y completar SIAF, unidad ejecutora, "
                "RUC y líneas de combustible antes de evaluar."
            ),
        }
        ruta_verdad.write_text(
            json.dumps(verdad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        total += 1
        print(f"{fuente.name}: {resultado.metodo}, {resultado.estado}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", type=Path, default=Path.home() / "Downloads" / "ordenes")
    parser.add_argument("--limite", type=int, default=50)
    parser.add_argument("--documentos", type=Path, default=RAIZ / "datos" / "documentos")
    parser.add_argument("--verdades", type=Path, default=RAIZ / "datos" / "verdad_terreno")
    args = parser.parse_args()
    total = importar(args.origen, args.limite, args.documentos, args.verdades)
    print(f"Importados {total} documentos; verdades en borrador requieren revisión.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

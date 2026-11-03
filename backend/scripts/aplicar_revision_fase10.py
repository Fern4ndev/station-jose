"""Incorpora al JSON las correcciones humanas marcadas en el CSV de revisión."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.core.ruc import es_valido as ruc_valido

RAIZ = Path(__file__).resolve().parents[1]
CSV_REVISION = RAIZ / "datos" / "revision_verdad_terreno.csv"
VERDADES = RAIZ / "datos" / "verdad_terreno"


def fecha_iso(texto: str) -> str:
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date().isoformat()


def aplicar(ruta_csv: Path) -> tuple[int, int]:
    aplicadas = 0
    pendientes = 0
    with ruta_csv.open(encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            ruta_verdad = VERDADES / f"{Path(fila['archivo']).name}.json"
            verdad = json.loads(ruta_verdad.read_text(encoding="utf-8"))
            if (fila.get("revisada") or "").strip().casefold() not in {
                "si",
                "sí",
                "ok",
                "revisada",
            }:
                pendientes += 1
                continue
            ruc_proveedor = fila["ruc_proveedor"].strip()
            ruc_unidad = fila["ruc_unidad_ejecutora"].strip()
            if not ruc_valido(ruc_proveedor) or not ruc_valido(ruc_unidad):
                raise ValueError(
                    f"{fila['archivo']}: revise los RUC; ambos deben pasar "
                    "el dígito verificador."
                )
            if not fila["partidas_json"].strip():
                raise ValueError(f"{fila['archivo']}: falta revisar las partidas.")
            verdad["campos"] = {
                "numero_orden": fila["numero_orden"].strip(),
                "fecha": fecha_iso(fila["fecha_dd_mm_aaaa"]),
                "monto": f"{Decimal(fila['monto_soles'].strip()):.2f}",
                "institucion": fila["proveedor"].strip(),
            }
            verdad["datos_orden"].update(
                {
                    "numero_siaf": fila["numero_siaf"].strip(),
                    "proveedor": {
                        **verdad["datos_orden"]["proveedor"],
                        "razon_social": fila["proveedor"].strip(),
                        "ruc": ruc_proveedor,
                        "direccion": fila.get("direccion_proveedor", "").strip() or None,
                    },
                    "sede_estacion": fila["sede"].strip(),
                    "unidad_ejecutora": fila["unidad_ejecutora"].strip(),
                    "ruc_unidad_ejecutora": ruc_unidad,
                    "partidas_combustible": json.loads(fila["partidas_json"]),
                }
            )
            verdad["revisada_dos_pasadas"] = True
            verdad["borrador_generado_por_ocr"] = False
            verdad["estado_revision"] = "revisada_dos_pasadas"
            verdad["notas"] = fila.get("correcciones_usuario", "").strip()
            ruta_verdad.write_text(
                json.dumps(verdad, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            aplicadas += 1
    return aplicadas, pendientes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_REVISION)
    args = parser.parse_args()
    aplicadas, pendientes = aplicar(args.csv)
    print(f"Verdades terreno revisadas incorporadas: {aplicadas}; pendientes: {pendientes}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

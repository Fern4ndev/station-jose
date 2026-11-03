"""Extrae encabezado y partidas de PDFs de órdenes escaneadas.

Guarda datos y evidencia OCR localmente en `datos/resultados_ordenes/`.
Los campos ilegibles quedan nulos o con una advertencia; nunca se deducen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.services.ocr.orden_compra import extraer_campos  # noqa: E402


def ocr_pdf(ruta: Path, dpi: int, timeout: float) -> dict:
    from app.services.ocr import extractor, lector, preprocesado, rapidocr

    documento = lector.leer(ruta.read_bytes(), dpi=dpi, maximo_paginas=10)
    palabras = list(documento.palabras)
    if documento.metodo == lector.TIPO_OCR:
        for indice, imagen in enumerate(documento.paginas):
            preparado = preprocesado.preparar(imagen, preprocesado.Pasos())
            palabras.extend(rapidocr.leer(preparado, timeout_segundos=timeout, pagina=indice))
    renglones = extractor.agrupar_lineas(palabras)
    lineas = [texto for _, texto, _ in renglones]
    texto = "\n".join(lineas)
    return {
        "archivo": ruta.name,
        "metodo": documento.metodo,
        "paginas": len(documento.paginas)
        if documento.paginas
        else len({p.pagina for p in palabras}),
        "campos": extraer_campos(texto, lineas),
        "texto_ocr": texto,
    }


def guardar_json(ruta: Path, datos: list[dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def procesar(origen: Path, salida: Path, limite: int, dpi: int, timeout: float) -> int:
    salida.mkdir(parents=True, exist_ok=True)
    resultados: list[dict] = []
    huellas: dict[str, str] = {}
    archivos = sorted(origen.glob("*.pdf"))
    for ruta in archivos:
        huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
        if huella in huellas:
            print(f"DUPLICADO: {ruta.name} = {huellas[huella]}", flush=True)
            continue
        huellas[huella] = ruta.name
        if limite and len(resultados) >= limite:
            break
        try:
            resultado = ocr_pdf(ruta, dpi, timeout)
        except Exception as exc:
            resultado = {
                "archivo": ruta.name,
                "metodo": "fallido",
                "paginas": 0,
                "campos": {
                    "advertencias": [f"Fallo al procesar el documento: {type(exc).__name__}: {exc}"]
                },
                "texto_ocr": "",
            }
        resultados.append(resultado)
        guardar_json(salida / "ordenes_extraidas.json", resultados)
        campos = resultado["campos"]
        partida_count = len(campos.get("partidas_combustible", []))
        etiqueta = (
            f"{len(resultados):02d}/"
            f"{min(limite or len(archivos), len(archivos))}: "
            f"{ruta.name} | {campos.get('numero_orden')} | "
            f"{partida_count} partidas | {resultado['metodo']}"
        )
        print(etiqueta, flush=True)

    guardar_csv(salida, resultados)
    return len(resultados)


def guardar_csv(carpeta: Path, resultados: list[dict]) -> None:
    ordenes = carpeta / "resumen_ordenes.csv"
    with ordenes.open("w", newline="", encoding="utf-8-sig") as archivo:
        columnas = [
            "archivo",
            "numero_orden",
            "numero_siaf",
            "fecha_dia_mes_anio",
            "fecha",
            "proveedor",
            "ruc_proveedor",
            "direccion_proveedor",
            "sede_estacion",
            "codigo_unidad_ejecutora",
            "unidad_ejecutora",
            "ruc_unidad_ejecutora",
            "advertencias",
        ]
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for resultado in resultados:
            campos = resultado["campos"]
            proveedor = campos.get("proveedor") or {}
            escritor.writerow(
                {
                    "archivo": resultado["archivo"],
                    "numero_orden": campos.get("numero_orden"),
                    "numero_siaf": campos.get("numero_siaf"),
                    "fecha_dia_mes_anio": campos.get("fecha_dia_mes_anio"),
                    "fecha": campos.get("fecha"),
                    "proveedor": proveedor.get("razon_social"),
                    "ruc_proveedor": proveedor.get("ruc"),
                    "direccion_proveedor": proveedor.get("direccion"),
                    "sede_estacion": campos.get("sede_estacion"),
                    "codigo_unidad_ejecutora": campos.get("codigo_unidad_ejecutora"),
                    "unidad_ejecutora": campos.get("unidad_ejecutora"),
                    "ruc_unidad_ejecutora": campos.get("ruc_unidad_ejecutora"),
                    "advertencias": " | ".join(campos.get("advertencias", [])),
                }
            )
    partidas = carpeta / "partidas_combustible.csv"
    with partidas.open("w", newline="", encoding="utf-8-sig") as archivo:
        columnas = [
            "archivo",
            "numero_orden",
            "numero_siaf",
            "codigo",
            "descripcion",
            "cantidad",
            "unidad_medida",
            "precio_unitario",
            "precio_total",
            "evidencia",
        ]
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for resultado in resultados:
            campos = resultado["campos"]
            for partida in campos.get("partidas_combustible", []):
                escritor.writerow(
                    {
                        "archivo": resultado["archivo"],
                        "numero_orden": campos.get("numero_orden"),
                        "numero_siaf": campos.get("numero_siaf"),
                        **partida,
                    }
                )


def reextraer_resultados(salida: Path) -> int:
    """Reaplica las reglas a los textos OCR ya guardados, sin repetir OCR."""
    ruta = salida / "ordenes_extraidas.json"
    resultados = json.loads(ruta.read_text(encoding="utf-8"))
    for resultado in resultados:
        texto = resultado.get("texto_ocr", "")
        resultado["campos"] = extraer_campos(texto, texto.splitlines())
    huellas: dict[str, str] = {}
    for resultado in resultados:
        archivo = resultado.get("archivo", "")
        ruta_pdf = RAIZ / "datos" / "documentos" / archivo
        if not ruta_pdf.is_file():
            ruta_pdf = Path.home() / "Downloads" / "ordenes" / archivo
        if ruta_pdf.is_file():
            huella = hashlib.sha256(ruta_pdf.read_bytes()).hexdigest()
            resultado["sha256"] = huella
            resultado["duplicado_de"] = huellas.get(huella)
            huellas.setdefault(huella, archivo)
        campos = resultado["campos"]
        campos["partidas_total_confirmadas"] = sum(
            (Decimal(fila["precio_total"]) for fila in campos["partidas_combustible"]),
            start=Decimal("0"),
        ).quantize(Decimal("0.01"))
        campos["partidas_total_confirmadas"] = format(campos["partidas_total_confirmadas"], "f")
    guardar_json(ruta, resultados)
    guardar_csv(salida, resultados)
    return len(resultados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", type=Path, default=Path.home() / "Downloads" / "ordenes")
    parser.add_argument("--salida", type=Path, default=RAIZ / "datos" / "resultados_ordenes")
    parser.add_argument("--limite", type=int, default=0, help="0 procesa todos los PDF únicos")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument(
        "--reextraer",
        action="store_true",
        help="reconstruye campos y CSV desde el OCR guardado, sin volver a leer los PDF",
    )
    args = parser.parse_args()
    total = (
        reextraer_resultados(args.salida)
        if args.reextraer
        else procesar(args.origen, args.salida, args.limite, args.dpi, args.timeout)
    )
    print(f"Procesados {total} PDF únicos. Resultados: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

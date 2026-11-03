"""Sugiere la institución compradora usando el RUC de facturación de la orden."""

from __future__ import annotations

import re

from app.core.ruc import es_valido as ruc_valido
from app.services.ocr import extractor
from app.services.ocr.lector import Palabra

ETIQUETA_FACTURAR = re.compile(r"\bF\w{2,10}\s+a\s+nombre\s+de\b", re.IGNORECASE)
ETIQUETA_CORTE = re.compile(r"\b(?:direcci[oó]n|r\s*u\s*c|agradecemos)\b", re.IGNORECASE)
DIGITOS = re.compile(r"(?<!\d)(\d[\d\s]{9,14})(?!\d)")


def desde_palabras(palabras: tuple[Palabra, ...] | list[Palabra]) -> dict | None:
    """Busca el RUC en el bloque «Facturar a nombre de», nunca en el proveedor.

    El documento puede partir el rótulo, el nombre y el RUC en renglones
    diferentes; solo se considera una ventana corta después de esa ancla.
    """
    renglones = extractor.agrupar_lineas(palabras)
    for indice, (_, texto_linea, _) in enumerate(renglones):
        ancla = ETIQUETA_FACTURAR.search(texto_linea)
        if ancla is None:
            continue
        nombre_partes: list[str] = []
        ruc_encontrado: str | None = None
        palabras_nombre: list[Palabra] = []
        palabras_ruc: list[Palabra] = []
        for desplazamiento, (palabras_cerca, texto_cerca, _) in enumerate(
            renglones[indice : indice + 5]
        ):
            desde = ancla.end() if desplazamiento == 0 else 0
            segmento = texto_cerca[desde:]
            ruc_match = DIGITOS.search(segmento)
            texto_nombre = segmento[: ruc_match.start()] if ruc_match else segmento
            texto_nombre = ETIQUETA_CORTE.split(texto_nombre, maxsplit=1)[0]
            texto_nombre = re.sub(r"^[\s:;,.]+|[\s:;,.]+$", "", texto_nombre)
            if texto_nombre:
                nombre_partes.append(texto_nombre)
                palabras_nombre.extend(palabras_cerca)
            if ruc_match:
                digitos = re.sub(r"\D", "", ruc_match.group(1))
                if ruc_valido(digitos):
                    ruc_encontrado = digitos
                    palabras_ruc.extend(palabras_cerca)
                    break
        if not ruc_encontrado:
            continue
        nombre = " ".join(" ".join(nombre_partes).split())
        nombre = re.split(r"\b(?:direcci[oó]n|r\s*u\s*c)\b", nombre, maxsplit=1, flags=re.I)[0]
        nombre = nombre.strip(" :;,.\t")
        evidencia = palabras_nombre + palabras_ruc
        confianza = (
            sum(palabra.confianza for palabra in evidencia) / len(evidencia) if evidencia else 0.0
        )
        return {
            "nombre": nombre or None,
            "ruc": ruc_encontrado,
            "confianza": round(confianza, 4),
        }
    return None

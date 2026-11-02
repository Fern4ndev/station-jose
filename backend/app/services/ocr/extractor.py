"""Extracción de campos por etiquetas y anclas (Fase 9, plan sección 6).

La entrada es la lista de `Palabra` del lector (la misma estructura para
texto digital y para OCR). El extractor agrupa las palabras en líneas, busca
las etiquetas del documento —el valor va a la derecha de la etiqueta o debajo
de ella— y, como respaldo de segundo nivel, aplica patrones fijos de valor.

Regla del plan: campo no hallado queda con valor vacío y confianza 0, nunca
se inventa; los valores pasan por el normalizador antes de entregarse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from app.services.ocr import normalizador
from app.services.ocr.lector import Palabra

CAMPOS = ("numero_orden", "fecha", "monto", "institucion")

# Etiquetas del documento: se buscan en el texto de la línea sin distinguir
# mayúsculas. El valor empieza después del final del texto etiquetado.
ANCLAS: dict[str, tuple[re.Pattern[str], ...]] = {
    "numero_orden": (re.compile(r"orden\s+de\s+compra", re.IGNORECASE),),
    "fecha": (re.compile(r"\bfecha\b", re.IGNORECASE),),
    "monto": (re.compile(r"\bmonto\b|\bpresupuesto\b", re.IGNORECASE),),
    "institucion": (re.compile(r"\bse[nñ]ores\b", re.IGNORECASE),),
}

# Respaldo por patrón de valor cuando la etiqueta no deja valor a la derecha
# ni debajo. La institución no tiene patrón fiable: sin etiqueta, no hay dato.
PATRONES: dict[str, re.Pattern[str] | None] = {
    "numero_orden": re.compile(r"\b\d{1,8}\s*[-–]\s*20\d{2}\b"),
    "fecha": re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}\b"),
    "monto": re.compile(r"\bs\s*/\s*\.?\s*\d[\d.,]*"),
    "institucion": None,
}

# Renglón empaquetado: las palabras en orden X, el texto corrido y la
# posición de inicio de cada palabra dentro de ese texto.
Renglon = tuple[tuple[Palabra, ...], str, tuple[int, ...]]


@dataclass(frozen=True)
class CampoExtraido:
    """Un campo crudo: valor normalizado, texto bruto y palabras del valor."""

    clave: str
    valor: str
    bruto: str
    palabras: tuple[Palabra, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class _Crudo:
    """Valor leído alrededor de una etiqueta, todavía sin normalizar."""

    texto: str
    palabras: tuple[Palabra, ...] = ()


def agrupar_lineas(
    palabras: tuple[Palabra, ...] | list[Palabra],
) -> list[Renglon]:
    """Empaqueta las palabras por página y renglón, en orden de lectura.

    La tolerancia vertical es un porcentaje del alto mediano de las palabras:
    letras pequeñas dentro de una línea no abren renglones falsos.
    """
    ordenadas = sorted(palabras, key=lambda p: (p.pagina, p.centro_y, p.x0))
    if not ordenadas:
        return []
    tolerancia = max(median(p.altura for p in ordenadas) * 0.6, 1.0)
    grupos: list[list[Palabra]] = [[]]
    centro: float | None = None
    pagina_previa = ordenadas[0].pagina
    for palabra in ordenadas:
        if grupos[-1]:
            cambia_pagina = palabra.pagina != pagina_previa
            salta_linea = (
                centro is not None and abs(palabra.centro_y - centro) > tolerancia
            )
            if cambia_pagina or salta_linea:
                grupos.append([])
                centro = None
        if centro is None:
            centro = palabra.centro_y
        else:  # el centro del renglón sigue el promedio de sus palabras
            centro = (centro + palabra.centro_y) / 2
        grupos[-1].append(palabra)
        pagina_previa = palabra.pagina
    return [empaquetar(renglon) for renglon in grupos if renglon]


def empaquetar(renglon: list[Palabra]) -> Renglon:
    """Ordena un renglón por X y arma su texto con el índice de cada palabra."""
    ordenadas = tuple(sorted(renglon, key=lambda p: p.x0))
    texto = " ".join(p.texto for p in ordenadas)
    inicios: list[int] = []
    acumulado = 0
    for palabra in ordenadas:
        inicios.append(acumulado)
        acumulado += len(palabra.texto) + 1
    return ordenadas, texto, tuple(inicios)


def extraer(
    palabras: tuple[Palabra, ...] | list[Palabra],
) -> dict[str, CampoExtraido]:
    """Extrae los campos del plan; sin pista, el campo queda con valor vacío."""
    renglones = agrupar_lineas(palabras)
    encontrados: dict[str, CampoExtraido] = {
        clave: CampoExtraido(clave=clave, valor="", bruto="") for clave in CAMPOS
    }
    for clave in CAMPOS:
        crudo = _por_ancla(clave, renglones) or _por_patron(clave, renglones)
        if crudo is None:
            continue
        campo = _normalizar(clave, crudo)
        if campo is not None:
            encontrados[clave] = campo
    return encontrados


def _por_ancla(clave: str, renglones: list[Renglon]) -> _Crudo | None:
    """Busca el valor a la derecha de la etiqueta y, si no, debajo de ella."""
    for ancla in ANCLAS[clave]:
        for tema, (palabras_linea, texto, inicios) in enumerate(renglones):
            cuadro = ancla.search(texto)
            if cuadro is None:
                continue
            # El OCR de línea trae etiqueta y valor en la misma palabra, así
            # que el segmento puede empezar a mitad de una palabra.
            valor = _segmento(palabras_linea, texto, inicios, desde=cuadro.end())
            if valor.texto:
                return valor
            # Debajo: hasta dos líneas, cortando si la baja parece otra
            # etiqueta del mismo campo (no se mezclan dos etiquetas).
            for abajo in (tema + 1, tema + 2):
                if abajo >= len(renglones):
                    break
                palabras_bajo, texto_bajo, inicios_bajo = renglones[abajo]
                if _etiqueta_en(clave, texto_bajo):
                    break
                segmento = _segmento(palabras_bajo, inicios_bajo, desde=0)
                if segmento.texto:
                    return segmento
    return None


def _etiqueta_en(clave: str, texto: str) -> bool:
    """True si el texto de la línea contiene una etiqueta del campo."""
    return any(ancla.search(texto) for ancla in ANCLAS[clave])


def _segmento(
    palabras_linea: tuple[Palabra, ...],
    texto_linea: str,
    inicios: tuple[int, ...],
    *,
    desde: int,
) -> _Crudo:
    """Las palabras del renglón a partir de `desde`, partiendo la ciñe.

    El texto corrido del renglón es la fuente de verdad: la etiqueta y el
    valor pueden convivir dentro de una misma palabra del OCR (`SEÑORES:
    INSTITUCION ...`). En ese caso la palabra se divide según el ancho por
    carácter de su caja, y el valor conserva la confianza original del renglón.
    """
    if desde >= len(texto_linea):
        return _Crudo(texto="", palabras=())
    seleccionadas: list[Palabra] = []
    for palabra, inicio in zip(palabras_linea, inicios, strict=True):
        fin = inicio + len(palabra.texto)
        if fin <= desde:
            continue  # la palabra es toda etiqueta (o texto anterior)
        if inicio >= desde:
            seleccionadas.append(palabra)
            continue
        # La etiqueta y el valor comparten palabra: partición proporcional
        # del texto y de la caja. La confianza es del renglón, no del recorte.
        corte = desde - inicio
        ancho_letra = (palabra.x1 - palabra.x0) / max(len(palabra.texto), 1)
        seleccionadas.append(
            Palabra(
                texto=palabra.texto[corte:].strip(),
                x0=palabra.x0 + ancho_letra * corte,
                y0=palabra.y0,
                x1=palabra.x1,
                y1=palabra.y1,
                confianza=palabra.confianza,
                pagina=palabra.pagina,
            )
        )
    texto = " ".join(palabra.texto for palabra in seleccionadas if palabra.texto).strip()
    return _Crudo(texto=texto, palabras=tuple(seleccionadas))


def _por_patron(clave: str, renglones: list[Renglon]) -> _Crudo | None:
    """Respaldo: busca el patrón fijo del valor recorriendo todas las líneas."""
    patron = PATRONES.get(clave)
    if patron is None:
        return None
    for palabras_linea, texto, inicios in renglones:
        cuadro = patron.search(texto)
        if cuadro is None:
            continue
        seleccionadas = []
        for palabra, inicio in zip(palabras_linea, inicios, strict=True):
            fin = inicio + len(palabra.texto)
            if inicio < cuadro.end() and fin > cuadro.start():
                seleccionadas.append(palabra)
        return _Crudo(texto=cuadro.group(0), palabras=tuple(seleccionadas))
    return None


def _normalizar(clave: str, crudo: _Crudo) -> CampoExtraido | None:
    """Convierte el valor crudo según el campo: sin valor válido, no entrega."""
    texto_bruto = normalizador.agrupar_texto(crudo.texto)
    if clave == "numero_orden":
        valor = normalizador.normalizar_numero(texto_bruto) or ""
    elif clave == "fecha":
        valor = normalizador.normalizar_fecha(texto_bruto) or ""
    elif clave == "monto":
        valor = normalizador.normalizar_monto(texto_bruto) or ""
    elif clave == "institucion":
        # La etiqueta y los dos puntos quedaron en la misma palabra del OCR
        # que el valor; se sueltan también los separadores del arranque.
        limpio = re.sub(
            r"^(?:se[nñ]ores?)?\s*[:,.;]?\s*", "", texto_bruto, flags=re.IGNORECASE
        )
        valor = normalizador.agrupar_texto(limpio)
    else:  # pragma: no cover - el catálogo de campos es una constante
        valor = ""
    if not valor:
        return None
    return CampoExtraido(clave=clave, valor=valor, bruto=texto_bruto, palabras=crudo.palabras)

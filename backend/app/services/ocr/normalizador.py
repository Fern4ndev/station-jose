"""Normalización de los valores que salen de la lectura (Fase 9, plan sección 6).

Transforma el ruido de un documento real en los valores que espera la API:
fechas a ISO, montos a cadena decimal con redondeo a 2 decimales
(ROUND_HALF_UP), el RUC verificado con su dígito, la numeración de la orden y
el combustible contra el catálogo con coincidencia aproximada.

Regla del plan: campo no hallado o ilegible devuelve None y nunca se inventa.
Ninguna función de aquí devuelve un valor que el documento no traía.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from difflib import SequenceMatcher

from app.core.ruc import es_valido as ruc_valido

MINIMO_SIMILITUD = 0.82

# Confusiones típicas del OCR en campos numéricos (plan: O por 0, l por 1,
# S por 5; se agrega I por 1 y B por 8, trazos de escritura equivalentes).
CONFUSIONES = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "B": "8"})

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,  # variante usada en Perú
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def desacentuar(texto: str) -> str:
    """Versión ASCII de un texto, para comparar sin tildes."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra))


def normalizar_fecha(texto: str) -> str | None:
    """Fecha del documento en ISO (`2027-03-15`), o None si no es una fecha.

    Acepta `15/03/2027`, `15-03-2027`, `15.03.2027`, `2027-03-15` y la forma
    escrita `15 de marzo de 2027`. El año de 2 dígitos no se acepta: en una
    orden de compra esa ambigüedad no tiene rol.
    """
    limpio = texto.strip()
    dia_pipe = re.search(r"(?<![\d\.])(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(?![\d/])", limpio)
    if dia_pipe:
        return _validar(int(dia_pipe.group(3)), int(dia_pipe.group(2)), int(dia_pipe.group(1)))
    iso = re.search(r"(?<![\d/])(\d{4})-(\d{1,2})-(\d{1,2})(?![\d/])", limpio)
    if iso:
        anio, mes, dia = (int(grupo) for grupo in iso.groups())
        return _validar(anio, mes, dia)
    escrito = re.search(
        r"(\d{1,2})\s+de\s+([a-záéíóúü]+)\s+(?:de\s+)?(\d{4})", limpio, re.IGNORECASE
    )
    if escrito:
        mes = MESES.get(desacentuar(escrito.group(2)).casefold())
        if mes:
            return _validar(int(escrito.group(3)), mes, int(escrito.group(1)))
    return None


def _validar(anio: int, mes: int, dia: int) -> str | None:
    """ISO si la fecha existe; None si el día o el mes no encajan."""
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        return None


def normalizar_monto(texto: str) -> str | None:
    """Monto a cadena decimal con 2 decimales (`S/ 1,500.00` → `1500.00`).

    Acepta los dos estilos de los documentos reales: `S/ 1,500.00` (punto
    decimal, coma de miles) y `1.500,00` (decimal europeo). Quién es el
    separador decimal lo declara el último separador de la cifra: el otro es
    de miles y se retira.
    """
    limpio = texto.strip()
    # Retira lo que rodea a la cifra — restos de etiqueta y símbolo de
    # moneda, donde caiga en el prefijo — antes de sustituir confusiones:
    # una S quedaría leída como 5 y el monto saldría 5/ 1,500.00.
    limpio = limpio.lstrip(":;., ")
    moneda = re.search(r"s\s*/\s*\.?\s*", limpio, flags=re.IGNORECASE)
    if moneda:
        limpio = limpio[moneda.end():]
    limpio = re.sub(r"\bsoles?\b", "", limpio, flags=re.IGNORECASE)
    # Las confusiones del OCR tocan solo los tokens que ya parecen cifras
    # (contienen algún dígito): una palabra suelta (`alguna`) no se avanza
    # a numeral por la `l` que le sale en medio.
    limpio = "".join(
        token.translate(CONFUSIONES) if re.search(r"\d", token) else token
        for token in re.split(r"(\s+)", limpio)
    )
    cifra = re.sub(r"[^\d.,\-]", "", limpio)
    if not re.search(r"\d", cifra):
        return None
    negativo = cifra.startswith("-")
    cifra = cifra.lstrip("-")
    ultima_coma = cifra.rfind(",")
    ultimo_punto = cifra.rfind(".")
    decimal = "," if ultima_coma > ultimo_punto else "."
    miles = "." if decimal == "," else ","
    cifra = cifra.replace(miles, "")
    cifra = cifra.replace(decimal, ".")
    # Varios puntos o comas sobrantes: cifra mal leída, mejor rechazarla.
    if cifra.count(".") > 1:
        return None
    try:
        monto = Decimal(cifra).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    if monto.is_zero():
        return "0.00"
    return ("-" if negativo else "") + f"{monto:f}"


def normalizar_numero(texto: str) -> str | None:
    """Numeración de la orden: dígitos y guiones (`N° 0018-2026` → `0018-2026`).

    Las etiquetas (`N°`, `N.º`, `#`) se sueltan antes de sustituir confusiones,
    para no convertir una letra que es parte de la etiqueta en un dígito que
    el documento no traía.
    """
    limpio = texto.strip()
    limpio = re.sub(
        r"^(?:n[°ºo]\b|num(?:ero)?\b|orden\b|#)\s*[:#.]?\s*",
        "",
        limpio,
        flags=re.IGNORECASE,
    )
    limpio = limpio.replace("–", "-").replace("—", "-")  # noqa: RUF001
    limpio = limpio.translate(CONFUSIONES)
    numero = re.sub(r"[^\d.\-]", "", limpio)
    numero = re.sub(r"-{2,}", "-", numero).strip(".")
    numero = numero.strip("-") if numero.count("-") > 1 else numero
    return numero if re.search(r"\d", numero) else None


def normalizar_ruc(texto: str) -> str | None:
    """RUC de 11 dígitos con su dígito verificador; None si no cuadra."""
    limpio = texto.strip().translate(CONFUSIONES)
    digitos = "".join(letra for letra in limpio if letra.isdigit())
    return digitos if ruc_valido(digitos) else None


def normalizar_combustible(
    texto: str, catalogo: tuple[str, ...] | list[str], *, minimo: float = MINIMO_SIMILITUD
) -> str | None:
    """El combustible del catálogo más parecido al texto; None si no convence.

    La comparación quita signos, tildes y dobles espacios antes del ratio:
    `DIESEL B5` casa con `Diésel B5` y `GA-SOHOL 90` con `Gasohol 90`.
    """
    if not catalogo:
        return None
    leido = desacentuar(texto).casefold()
    leido = " ".join(leido.split())
    if not leido:
        return None
    candidatos = [" ".join(desacentuar(nombre).casefold().split()) for nombre in catalogo]
    for indice, nombre in enumerate(candidatos):
        if nombre and (nombre == leido or nombre in leido or leido in nombre):
            return catalogo[indice]
    leido = "".join(letra for letra in leido if letra.isalnum() or letra.isspace())
    leido = " ".join(leido.split())
    if not leido:
        return None
    mejor: tuple[float, int] | None = None
    for indice, nombre in enumerate(candidatos):
        ratio = SequenceMatcher(None, leido, nombre).ratio()
        if mejor is None or ratio > mejor[0]:
            mejor = (ratio, indice)
    if mejor and mejor[0] >= minimo:
        return catalogo[mejor[1]]
    return None


def agrupar_texto(texto: str) -> str:
    """Junta espacios extra y recorta alrededor, uso común para los campos."""
    return " ".join(texto.split()).strip()

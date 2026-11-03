"""Orquestación del OCR (Fase 9, plan sección 6).

Una llamada a `procesar` lleva el documento de bytes a la extracción con su
confianza por campo: clasificación y lectura (lector), preprocesado y motor
(si es escaneo), extracción y normalización, y cálculo de confianza.

La confianza sigue el plan: en texto digital es fija y alta salvo que el
valor no valide su formato; en OCR es el promedio de las palabras del valor,
penalizado a la mitad si el formato no valida. Un campo por debajo del umbral
queda con `requiere_revision` para la revisión en pantalla de la Fase 11.

La concurrencia se controla con un semáforo de proceso: sin turno en pocos
segundos, el error `OCR_OCUPADO` (503) deja libre a quien llama, sin colas.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Final

from app.errors import ErrorDominio
from app.services.ocr import extractor, lector, orden_compra, preprocesado, rapidocr, sugerencia
from app.services.ocr.preprocesado import Pasos

# Penalización aplicada a la confianza de un valor de OCR cuyo formato no valida.
PENALIZACION_FORMATO: Final[float] = 0.5
CONFIANZA_MINIMA: Final[float] = 0.0

MOTIVO_TIEMPO = "OCR_TIMEOUT"
MOTIVO_ILEGIBLE = "DOCUMENTO_ILEGIBLE"

# Formatos que se exigen a los valores normalizados.
FECHA_VALIDA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTO_VALIDO = re.compile(r"^-?\d+\.\d{2}$")
NUMERO_VALIDO = re.compile(r"^\d{1,8}(?:-20\d{2})?$")  # serie por año opcional


@dataclass(frozen=True)
class Campo:
    """Campo listo para la API: valor bruto y normalizado con su confianza."""

    clave: str
    valor: str
    bruto: str
    confianza: float
    requiere_revision: bool


@dataclass(frozen=True)
class AjustesOcr:
    """Ajustes de la corrida; la API y el CLI los construyen por proceso."""

    dpi: int = 300
    paginas_max: int = 5
    megapixeles_max: float = 25.0
    tiempo_segundos: float = 120.0
    turno_segundos: float = 5.0
    umbral_confianza: float = 0.8
    concurrencia: int = 2
    pasos: Pasos = field(default_factory=Pasos)


@dataclass(frozen=True)
class Extraccion:
    """Resultado del pipeline; `motivo` explica el estado `fallida`."""

    estado: str  # 'lista' | 'fallida'
    metodo: str
    campos: tuple[Campo, ...]
    advertencias: tuple[str, ...]
    paginas: int
    tiempo_ms: int
    motivo: str = ""
    institucion_sugerida: dict | None = None
    datos_orden: dict | None = None


_turno: threading.Semaphore | None = None
_bloqueo_turno = threading.Lock()


def _semaphore(tamano: int) -> threading.Semaphore:
    """Semáforo del proceso, creado con el tamaño de la primera corrida.

    Cambiar la concurrencia de un proceso en caliente no es un caso real: se
    fija con el despliegue y el reinicio del servicio la relee.
    """
    global _turno
    if _turno is None:
        with _bloqueo_turno:
            if _turno is None:
                _turno = threading.Semaphore(max(1, tamano))
    return _turno


def reiniciar_concurrencia() -> None:
    """Suelta el semáforo; pensado para pruebas."""
    global _turno
    with _bloqueo_turno:
        _turno = None


def procesar(contenido: bytes, *, ajustes: AjustesOcr | None = None) -> Extraccion:
    """Lee el documento y extrae los campos con su confianza por campo."""
    ajustes = ajustes or AjustesOcr()
    inicio = time.monotonic()
    documento = lector.leer(
        contenido,
        dpi=ajustes.dpi,
        maximo_paginas=ajustes.paginas_max,
        maximo_megapixeles=ajustes.megapixeles_max,
    )
    if documento.metodo == lector.TIPO_DIGITAL:
        crudos = extractor.extraer(documento.palabras)
        datos_orden = _datos_orden(documento.palabras)
        if all(not crudo.valor for crudo in crudos.values()) and not _hay_datos_orden(datos_orden):
            return _fallida(MOTIVO_ILEGIBLE, documento.metodo, 1, inicio)
        return _armar(
            crudos=crudos,
            metodo=documento.metodo,
            paginas=len(documento.paginas) or 1,
            confianza_digital=True,
            ajustes=ajustes,
            inicio=inicio,
            institucion_sugerida=sugerencia.desde_palabras(documento.palabras),
            datos_orden=datos_orden,
        )
    return _leer_ocr(documento, ajustes, inicio)


def _leer_ocr(documento: lector.DocumentoLeido, ajustes: AjustesOcr, inicio: float) -> Extraccion:
    """Turno de proceso, preprocesado y lectura de las páginas en secuencia."""
    semaforo = _semaphore(ajustes.concurrencia)
    if not semaforo.acquire(timeout=max(0.0, ajustes.turno_segundos)):
        raise ErrorDominio(
            503, "OCR_OCUPADO", "El motor de OCR está ocupado; reintente en unos segundos."
        )
    try:
        palabras: list[lector.Palabra] = []
        fecha_limite = inicio + ajustes.tiempo_segundos
        for indice, imagen in enumerate(documento.paginas):
            preparada = preprocesado.preparar(imagen, ajustes.pasos)
            restante = fecha_limite - time.monotonic()
            if restante <= 0:
                return _fallida(MOTIVO_TIEMPO, lector.TIPO_OCR, indice + 1, inicio)
            try:
                palabras.extend(rapidocr.leer(preparada, timeout_segundos=restante, pagina=indice))
            except rapidocr.TiempoAgotado:
                return _fallida(MOTIVO_TIEMPO, lector.TIPO_OCR, indice + 1, inicio)
    finally:
        semaforo.release()

    if not palabras:
        return _fallida(MOTIVO_ILEGIBLE, lector.TIPO_OCR, len(documento.paginas), inicio)
    crudos = extractor.extraer(tuple(palabras))
    datos_orden = _datos_orden(palabras)
    if all(not crudo.valor for crudo in crudos.values()) and not _hay_datos_orden(datos_orden):
        return _fallida(MOTIVO_ILEGIBLE, lector.TIPO_OCR, len(documento.paginas), inicio)
    return _armar(
        crudos=crudos,
        metodo=lector.TIPO_OCR,
        paginas=len(documento.paginas),
        confianza_digital=False,
        ajustes=ajustes,
        inicio=inicio,
        institucion_sugerida=sugerencia.desde_palabras(tuple(palabras)),
        datos_orden=datos_orden,
    )


def _datos_orden(palabras: tuple[lector.Palabra, ...] | list[lector.Palabra]) -> dict:
    """Extrae los campos SIGA y las partidas por combustible desde las líneas OCR."""
    lineas = [texto for _, texto, _ in extractor.agrupar_lineas(palabras)]
    return orden_compra.extraer_campos("\n".join(lineas), lineas)


def _hay_datos_orden(datos: dict) -> bool:
    """No clasifica como ilegible un documento que solo tenga datos estructurados."""
    proveedor = datos.get("proveedor") or {}
    return any(
        (
            datos.get("numero_orden"),
            datos.get("numero_siaf"),
            datos.get("fecha"),
            proveedor.get("razon_social"),
            proveedor.get("ruc"),
            datos.get("sede_estacion"),
            datos.get("unidad_ejecutora"),
            datos.get("ruc_unidad_ejecutora"),
            datos.get("partidas_combustible"),
        )
    )


def _armar(
    *,
    crudos: dict[str, extractor.CampoExtraido],
    metodo: str,
    paginas: int,
    confianza_digital: bool,
    ajustes: AjustesOcr,
    inicio: float,
    institucion_sugerida: dict | None = None,
    datos_orden: dict | None = None,
) -> Extraccion:
    """Calcula la confianza por campo, el estado final y las advertencias."""
    campos: list[Campo] = []
    advertencias: list[str] = []
    for clave in extractor.CAMPOS:
        crudo = crudos.get(clave, extractor.CampoExtraido(clave=clave, valor="", bruto=""))
        if not crudo.valor:
            campos.append(
                Campo(
                    clave=clave,
                    valor="",
                    bruto=crudo.bruto,
                    confianza=CONFIANZA_MINIMA,
                    requiere_revision=True,
                )
            )
            advertencias.append(f"{clave}: campo no identificado.")
            continue
        media = _confianza_de_palabras(crudo.palabras)
        formato_valido = _formato_valido(clave, crudo.valor)
        if confianza_digital:
            confianza = lector.CONFIANZA_DIGITAL
        else:
            confianza = media if formato_valido else media * PENALIZACION_FORMATO
        confianza = max(CONFIANZA_MINIMA, min(confianza, 1.0))
        requiere = not formato_valido or confianza < ajustes.umbral_confianza
        campos.append(
            Campo(
                clave=clave,
                valor=crudo.valor,
                bruto=crudo.bruto,
                confianza=confianza,
                requiere_revision=requiere,
            )
        )
        if not formato_valido:
            advertencias.append(f"{clave}: el valor '{crudo.valor}' no valida su formato.")
        elif requiere:
            advertencias.append(f"{clave}: confianza {confianza:.2f} bajo el umbral.")
    return Extraccion(
        estado="lista",
        metodo=metodo,
        campos=tuple(campos),
        advertencias=tuple(advertencias),
        paginas=paginas,
        tiempo_ms=int((time.monotonic() - inicio) * 1000),
        institucion_sugerida=institucion_sugerida,
        datos_orden=datos_orden,
    )


def _confianza_de_palabras(palabras: tuple[lector.Palabra, ...]) -> float:
    """Promedio de la confianza de las palabras del valor; 0 si no hay."""
    if not palabras:
        return CONFIANZA_MINIMA
    return sum(p.confianza for p in palabras) / len(palabras)


def _formato_valido(clave: str, valor: str) -> bool:
    """True si el valor normalizado cumple el formato esperado del campo."""
    if clave == "fecha":
        return bool(FECHA_VALIDA.fullmatch(valor))
    if clave == "monto":
        return bool(MONTO_VALIDO.fullmatch(valor))
    if clave == "numero_orden":
        return bool(NUMERO_VALIDO.fullmatch(valor))
    if clave == "institucion":
        return len(valor.strip()) >= 5
    return False


def _fallida(motivo: str, metodo: str, paginas: int, inicio: float) -> Extraccion:
    """Extracción que no produce datos: motivo estable para la Fase 11."""
    return Extraccion(
        estado="fallida",
        metodo=metodo,
        campos=(),
        advertencias=("La lectura no produjo campos utilizables.",),
        paginas=paginas,
        tiempo_ms=int((time.monotonic() - inicio) * 1000),
        motivo=motivo,
    )

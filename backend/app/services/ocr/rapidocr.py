"""Integración directa con RapidOCR (Fase 9, plan sección 6).

El motor se inicializa una única vez por proceso y se reutiliza en cada
lectura (`RapidOCR()` es lo más caro de la operación). La inferencia corre en
un grupo de hilos aparte para poder imponer un límite de tiempo por documento
sin procesos externos: si el modelo no carga, el pipeline recibe
`OCR_NO_DISPONIBLE` (503) y si el tiempo se agota, no se cae de la petición,
se avisa el motivo `OCR_TIMEOUT`.

`inferir` está aislada como función propia justamente para poder simular
motores lentos y lentos defectuosos en las pruebas unitarias.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from app.config import obtener_settings
from app.errors import ErrorDominio
from app.services.ocr.lector import Palabra

logger = logging.getLogger("app.ocr")

# El que devuelve el motor sobrepasa el tiempo de lectura por documento.
class TiempoAgotado(RuntimeError):
    """La lectura del motor superó el tiempo máximo acordado."""


def crear_motor() -> Any:
    """Carga única del modelo; separada para poder simular su falla."""
    from rapidocr import RapidOCR

    return RapidOCR()


_motor: Any = None
_bloqueo_motor = threading.Lock()
_pool: ThreadPoolExecutor | None = None
_bloqueo_pool = threading.Lock()


def reiniciar_motor() -> None:
    """Suelta el motor cargado; para pruebas y para cambiar de modelo."""
    global _motor
    with _bloqueo_motor:
        _motor = None


def obtener_motor() -> Any:
    """Devuelve el motor del proceso, cargándolo la primera vez."""
    global _motor
    if _motor is None:
        with _bloqueo_motor:
            if _motor is None:
                try:
                    _motor = crear_motor()
                except Exception as exc:  # falla de carga: nunca un 500 interno
                    logger.error("No se pudo inicializar RapidOCR: %s", exc)
                    raise ErrorDominio(
                        503,
                        "OCR_NO_DISPONIBLE",
                        "El motor de OCR no está disponible.",
                        {"detalle": str(exc)},
                    ) from exc
    return _motor


def _obtener_pool() -> ThreadPoolExecutor:
    """Grupo de hilos de inferencia; su tamaño es la concurrencia del OCR."""
    global _pool
    if _pool is None:
        with _bloqueo_pool:
            if _pool is None:
                workers = max(1, obtener_settings().ocr_concurrencia)
                _pool = ThreadPoolExecutor(
                    max_workers=workers, thread_name_prefix="ocr"
                )
    return _pool


def inferir(motor: Any, matriz: np.ndarray) -> tuple[str, np.ndarray, float]:
    """Llama al motor y devuelve (texto, caja, confianza) por cada hallazgo.

    RapidOCR 3.x entrega un `RapidOCROutput` con `.boxes` (N,4,2), `.txts` y
    `.scores`; si no hubo hallazgos, `boxes`/`txts` quedan en None.
    """
    salida = motor(matriz)
    if salida.boxes is None or salida.txts is None:
        return ()
    return tuple(
        (texto, np.asarray(caja), float(puntaje))
        for texto, caja, puntaje in zip(salida.txts, salida.boxes, salida.scores, strict=False)
    )


def leer(
    matriz: np.ndarray, *, timeout_segundos: float, pagina: int = 0
) -> tuple[Palabra, ...]:
    """Lee una matriz BGR y devuelve las palabras del OCR con su caja."""
    motor = obtener_motor()
    pool = _obtener_pool()
    futuro = pool.submit(inferir, motor, matriz)
    try:
        hallazgos = futuro.result(timeout=timeout_segundos)
    except TimeoutError as exc:
        futuro.cancel()  # sin efecto si ya corre: no se puede interrumpir
        raise TiempoAgotado(
            f"La lectura del OCR superó {timeout_segundos:g} s."
        ) from exc

    palabras: list[Palabra] = []
    for texto, caja, puntaje in hallazgos:
        xs = caja[:, 0]
        ys = caja[:, 1]
        palabras.append(
            Palabra(
                texto=str(texto),
                x0=float(xs.min()),
                y0=float(ys.min()),
                x1=float(xs.max()),
                y1=float(ys.max()),
                confianza=puntaje,
                pagina=pagina,
            )
        )
    # Sentido de lectura: de arriba a abajo, de izquierda a derecha.
    palabras.sort(key=lambda p: (p.centro_y, p.x0))
    return tuple(palabras)

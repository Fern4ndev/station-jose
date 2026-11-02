"""Preprocesado OpenCV de las páginas a imagen (Fase 9, plan sección 6).

Cada paso se activa o desactiva desde `AjustesOcr` para poder medir su efecto
sobre la exactitud del OCR en la Fase 10, cambiando de a uno. El orden es el
del plan: escala de grises, reducción de ruido, corrección de inclinación,
binarización adaptativa y escalado.

La salida siempre es una matriz escala de grises (el motor RapidOCR acepta
una sola matriz sin problema y de ahí nunca sale el color).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Longitud objetivo en píxeles del lado más largo: las fotos pequeñas se
# agrandan para que el detector encuentre las líneas de texto.
LADO_OBJETIVO = 1500

# Umbral de inclinación (grados) por debajo del cual no vale la pena girar.
INCLINACION_MINIMA = 0.25


@dataclass(frozen=True)
class Pasos:
    """Interruptores del preprocesado; todos activos por defecto."""

    gris: bool = True
    ruido: bool = True
    inclinacion: bool = True
    binarizacion: bool = True
    escalado: bool = True


def preparar(imagen: np.ndarray, pasos: Pasos | None = None) -> np.ndarray:
    """Aplica los pasos activos y devuelve la página lista para el motor."""
    pasos = pasos or Pasos()
    salida = imagen
    if pasos.escalado:
        salida = _agrandar(salida)
    if pasos.gris:
        salida = _a_grises(salida)
    if pasos.ruido:
        salida = _reducir_ruido(salida)
    if pasos.inclinacion:
        salida = _enderezar(salida)
    if pasos.binarizacion:
        salida = _binarizar(salida)
    return np.ascontiguousarray(salida)


def _a_grises(imagen: np.ndarray) -> np.ndarray:
    if imagen.ndim == 2:
        return imagen
    return cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)


def _reducir_ruido(imagen: np.ndarray) -> np.ndarray:
    """Filtro de mediana 3x3: quita el ruido de puntos conservando bordes."""
    return cv2.medianBlur(imagen, 3)


def _agrandar(imagen: np.ndarray) -> np.ndarray:
    """Escala la imagen hasta que el lado mayor alcance el objetivo."""
    altura, anchura = imagen.shape[:2]
    lado = max(altura, anchura)
    if lado >= LADO_OBJETIVO or lado == 0:
        return imagen
    factor = LADO_OBJETIVO / lado
    return cv2.resize(imagen, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def _enderezar(imagen: np.ndarray) -> np.ndarray:
    """Corrige la inclinación estimada con la caja mínima de los rasgos.

    La estimación busca el ángulo dominante de los bordes del documento; si
    es menor a un cuarto de grado, la imagen ya está derecha y se devuelve
    sin tocar (querer corregir medio grado sacrifica definición).
    """
    gris = _a_grises(imagen)
    esta = cv2.bitwise_not(cv2.Canny(gris, 50, 150))
    (filas, columnas) = esta.shape
    if min(filas, columnas) == 0:
        return imagen
    velocidad = cv2.minAreaRect(np.column_stack(np.where(esta > 0))[:, ::-1])[-1]
    angulo = velocidad
    # OpenCV >= 4.5 devuelve el ángulo en [0, 90): un rasgo a +5° reporta 85°,
    # que es lo mismo que estar inclinado -5° respecto a la horizontal.
    if angulo > 45:
        angulo = angulo - 90
    elif angulo < -45:
        angulo = angulo + 90
    if abs(angulo) < INCLINACION_MINIMA:
        return imagen
    alto, ancho = imagen.shape[:2]
    centro = (ancho / 2, alto / 2)
    rotacion = cv2.getRotationMatrix2D(centro, angulo, 1.0)
    return cv2.warpAffine(
        imagen,
        rotacion,
        (ancho, alto),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _binarizar(imagen: np.ndarray) -> np.ndarray:
    """Binarización adaptativa: garantiza texto oscuro sobre fondo claro."""
    gris = _a_grises(imagen)
    return cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )

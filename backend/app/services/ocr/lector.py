"""Lectura de documentos para el OCR (Fase 9, plan sección 6).

El lector clasifica el archivo por su firma real (nunca por la extensión),
extrae las palabras del texto digital del PDF con `pdfplumber` y, si el PDF
es un escaneo, renderiza cada página con `pypdfium2` a la densidad configurada
para que el motor RapidOCR la lea como imagen. Las imágenes JPG/PNG se
corrigen con la orientación EXIF de la cámara.

La salida es siempre una lista de `Palabra` cuando hay texto digital y una
lista de matrices BGR cuando toca OCR: la misma estructura de palabra para
ambos orígenes deja al extractor sin conocer de dónde viene.
"""

from __future__ import annotations

import io
import logging
import struct
from dataclasses import dataclass, field

import cv2
import numpy as np
import pdfplumber
import pypdfium2 as pdfium

from app.core.archivos import ErrorArchivo, sniff_formato

logger = logging.getLogger("app.ocr")

FORMATOS_LEIDOS = ("pdf", "jpg", "png")
TIPO_DIGITAL = "texto_digital"
TIPO_OCR = "ocr"

# El texto digital no sale de un modelo: su confianza es fija y alta, y solo
# se penaliza si el valor no valida su formato (lo decide el pipeline).
CONFIANZA_DIGITAL = 0.99

# Con menos de esta cantidad de caracteres el PDF es un escaneo y pasa por OCR.
MINIMO_CARACTERES_DIGITAL = 30

# Corrimiento artificial en el eje Y para separar las páginas de un PDF y
# que las líneas de una página nunca se mezclen con las de otra.
SEPARADOR_PAGINA = 10_000.0


@dataclass(frozen=True)
class Palabra:
    """Una palabra leída, con su caja, confianza, línea y página.

    La caja son coordenadas del sistema de su origen (unidades de PDF o
    píxeles de la imagen); bastan para anclar valores y para agrupar líneas.
    `linea` lo asigna el extractor con una tolerancia común a la página.
    """

    texto: str
    x0: float
    y0: float
    x1: float
    y1: float
    confianza: float
    linea: int = 0
    pagina: int = 0

    @property
    def altura(self) -> float:
        return self.y1 - self.y0

    @property
    def centro_y(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True)
class DocumentoLeido:
    """Resultado de la lectura: palabras y, si es escaneo, las páginas BGR."""

    metodo: str
    palabras: tuple[Palabra, ...]
    paginas: tuple[np.ndarray, ...] = field(default_factory=tuple)


def clasificar_formato(contenido: bytes) -> str:
    """Formato real del documento por su firma; error 415 si no es admitido."""
    formato = sniff_formato(contenido)
    if formato not in FORMATOS_LEIDOS:
        raise ErrorArchivo(
            415, "ARCHIVO_NO_PERMITIDO", "El documento debe ser PDF, JPG o PNG."
        )
    return formato


def leer(
    contenido: bytes,
    *,
    dpi: int = 300,
    maximo_paginas: int = 5,
    maximo_megapixeles: float = 25.0,
) -> DocumentoLeido:
    """Punto de entrada: clasifica y devuelve palabras o páginas a imagen."""
    formato = clasificar_formato(contenido)
    if formato == "pdf":
        return _leer_pdf(
            contenido,
            dpi=dpi,
            maximo_paginas=maximo_paginas,
            maximo_megapixeles=maximo_megapixeles,
        )
    matriz = _leer_imagen(contenido, formato)
    _exigir_megapixeles(matriz, 1, maximo_megapixeles)
    return DocumentoLeido(metodo=TIPO_OCR, palabras=(), paginas=(matriz,))


def _leer_pdf(
    contenido: bytes,
    *,
    dpi: int,
    maximo_paginas: int,
    maximo_megapixeles: float,
) -> DocumentoLeido:
    """Texto digital con pdfplumber; si es escaneo, renderiza con pypdfium2."""
    # La apertura puede lanzar la PDFSyntaxError de pdfminer (backend de
    # pdfplumber): se traduce a ARCHIVO_CORRUPTO. El bloque de extracción va
    # aparte para no convertir un ErrorArchivo propio en 500 interno.
    try:
        documento = pdfplumber.open(io.BytesIO(contenido))
    except Exception as exc:
        raise ErrorArchivo(
            422, "ARCHIVO_CORRUPTO", "El PDF no se puede abrir (archivo dañado)."
        ) from exc
    try:
        total = len(documento.pages)
        if total == 0:
            raise ErrorArchivo(
                422, "ARCHIVO_CORRUPTO", "El PDF no tiene páginas legibles."
            )
        if total > maximo_paginas:
            raise ErrorArchivo(
                413,
                "ARCHIVO_DEMASIADO_GRANDE",
                f"El documento tiene {total} páginas y el máximo es {maximo_paginas}.",
            )
        palabras: list[Palabra] = []
        for indice, pagina in enumerate(documento.pages):
            for palabra in pagina.extract_words():
                palabras.append(
                    Palabra(
                        texto=palabra["text"],
                        x0=float(palabra["x0"]),
                        # pdfplumber da `top` < `bottom` (origen arriba); ambos
                        # se guardan como caja y el corrimiento separa páginas.
                        y0=float(palabra["top"]) + indice * SEPARADOR_PAGINA,
                        x1=float(palabra["x1"]),
                        y1=float(palabra["bottom"]) + indice * SEPARADOR_PAGINA,
                        confianza=CONFIANZA_DIGITAL,
                        pagina=indice,
                    )
                )
    finally:
        documento.close()

    if sum(len(p.texto) for p in palabras) >= MINIMO_CARACTERES_DIGITAL:
        return DocumentoLeido(metodo=TIPO_DIGITAL, palabras=_ordenar_rasgo(palabras))

    logger.info(
        "PDF sin texto digital suficiente (%d caracteres): va por OCR.", len(palabras)
    )
    return DocumentoLeido(
        metodo=TIPO_OCR,
        palabras=(),
        paginas=_renderizar(contenido, dpi=dpi, maximo_megapixeles=maximo_megapixeles),
    )


def _renderizar(
    contenido: bytes, *, dpi: int, maximo_megapixeles: float
) -> tuple[np.ndarray, ...]:
    """Cada página del PDF a matriz BGR a la densidad pedida (pypdfium2)."""
    documento = pdfium.PdfDocument(contenido)
    try:
        matrices: list[np.ndarray] = []
        for indice, pagina in enumerate(documento):
            bitmap = pagina.render(scale=dpi / 72)
            matriz = bitmap.to_numpy()
            if matriz.ndim == 3 and matriz.shape[2] == 4:
                matriz = matriz[:, :, :3]  # descarta el canal alfa
            matriz = np.ascontiguousarray(matriz)
            _exigir_megapixeles(matriz, indice + 1, maximo_megapixeles)
            matrices.append(matriz)
            del bitmap  # libera la memoria nativa del mapa de bits pronto
            pagina.close()
        return tuple(matrices)
    except (RuntimeError, pdfium.PdfiumError) as exc:
        raise ErrorArchivo(
            422, "ARCHIVO_CORRUPTO", "El PDF no se pudo renderizar para el OCR."
        ) from exc
    finally:
        documento.close()


def _ordenar_rasgo(palabras: list[Palabra]) -> tuple[Palabra, ...]:
    """Numera `linea` como rasgo provisional del flujo de texto del PDF."""
    return tuple(
        Palabra(
            texto=p.texto,
            x0=p.x0,
            y0=p.y0,
            x1=p.x1,
            y1=p.y1,
            confianza=p.confianza,
            linea=orden,
            pagina=p.pagina,
        )
        for orden, p in enumerate(
            sorted(palabras, key=lambda a: (a.pagina, a.centro_y, a.x0))
        )
    )


def _leer_imagen(contenido: bytes, formato: str) -> np.ndarray:
    """JPG o PNG a matriz BGR, con la orientación EXIF corregida."""
    matriz = cv2.imdecode(np.frombuffer(contenido, dtype=np.uint8), cv2.IMREAD_COLOR)
    if matriz is None:
        raise ErrorArchivo(
            422, "ARCHIVO_CORRUPTO", "La imagen no se puede abrir (archivo dañado o vacío)."
        )
    if formato == "jpg":
        matriz = _corregir_orientacion(matriz, _orientacion_exif(contenido))
    return matriz


def _exigir_megapixeles(matriz: np.ndarray, pagina: int, maximo_megapixeles: float) -> None:
    """Corta la lectura si una página excede el límite de megapíxeles."""
    altura, anchura = matriz.shape[:2]
    megapixeles = altura * anchura / 1_000_000
    if megapixeles > maximo_megapixeles:
        raise ErrorArchivo(
            413,
            "ARCHIVO_DEMASIADO_GRANDE",
            f"La página {pagina} tiene {megapixeles:.1f} MP y el máximo es "
            f"{maximo_megapixeles:.1f} MP.",
        )


def _orientacion_exif(jpeg: bytes) -> int:
    """Orientación EXIF 1-8 de un JPEG; 1 (sin giro) si no la hay o es ilegible.

    Escanea los segmentos APP1 hasta encontrar "Exif\\0\\0" y lee la etiqueta
    0x0112 del TIFF interior. Un JPEG dañado nunca debe tumbar la lectura.
    """
    if jpeg[:2] != b"\xff\xd8":  # no es JPEG; el sniffing ya lo dejó pasar
        return 1
    try:
        indice = 2
        while indice + 6 < len(jpeg):
            if jpeg[indice] != 0xFF:
                return 1
            marca = jpeg[indice + 2 : indice + 4]
            longitud = int.from_bytes(jpeg[indice + 4 : indice + 6], "big")
            if longitud < 2:  # longitud inválida: se lee como sin giro
                return 1
            if marca == b"\xe1" and jpeg[indice + 6 : indice + 12] == b"Exif\x00\x00":
                return _leer_tiff_orientacion(jpeg[indice + 12 : indice + 2 + longitud])
            if marca == b"\xda":  # SOS: luego vienen los datos de imagen
                return 1
            indice += 2 + longitud
    except (IndexError, ValueError, struct.error):
        return 1
    return 1


def _leer_tiff_orientacion(tiff: bytes) -> int:
    """Etiqueta 0x0112 del primer IFD del TIFF; 1 si no aparece o es ilegible."""
    if len(tiff) < 8:
        return 1
    endian = {b"II": "<", b"MM": ">"}.get(tiff[:2])
    if endian is None or int.from_bytes(tiff[2:4], "big") != 42:
        return 1
    (offset_ifd,) = struct.unpack_from(endian + "I", tiff, 4)
    if offset_ifd + 2 > len(tiff):
        return 1
    (cantidad,) = struct.unpack_from(endian + "H", tiff, offset_ifd)
    for entrada in range(cantidad):
        base = offset_ifd + 2 + entrada * 12
        if base + 12 > len(tiff):
            return 1
        (etiqueta,) = struct.unpack_from(endian + "H", tiff, base)
        if etiqueta == 0x0112:
            (valor,) = struct.unpack_from(endian + "H", tiff, base + 8)
            return valor if 1 <= valor <= 8 else 1
    return 1


def _corregir_orientacion(imagen: np.ndarray, orientacion: int) -> np.ndarray:
    """Aplica la transformación del EXIF para mostrar la imagen derecha.

    Tabla del estándar: 2 espejo horizontal, 3 giro de 180°, 4 espejo
    vertical, 5/7 transposición con giro, 6 giro a la derecha, 8 a la
    izquierda. La orientación 1 (o cualquier otra) queda tal cual.
    """
    if orientacion == 2:
        return cv2.flip(imagen, 1)
    if orientacion == 3:
        return cv2.rotate(imagen, cv2.ROTATE_180)
    if orientacion == 4:
        return cv2.flip(imagen, 0)
    if orientacion == 5:
        girada = cv2.rotate(imagen, cv2.ROTATE_90_CLOCKWISE)
        return cv2.flip(girada, 1)
    if orientacion == 6:
        return cv2.rotate(imagen, cv2.ROTATE_90_CLOCKWISE)
    if orientacion == 7:
        girada = cv2.rotate(imagen, cv2.ROTATE_90_CLOCKWISE)
        return cv2.flip(girada, 0)
    if orientacion == 8:
        return cv2.rotate(imagen, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return imagen

"""Validación de archivos y almacenamiento privado (CFG-02, Fase 4; ordenes, Fase 5).

La extensión no es confianza: el cliente puede renombrar cualquier cosa.
Aquí se comprueba la firma binaria (magic bytes) del formato y el tamaño
máximo evita cargar en memoria algo enorme.

Fase 5 (ORD-03/04): documentos de órdenes con firmas PDF/JPG/PNG, carpeta
`almacenamiento/ordenes/{año}/{uuid}.{ext}` y lectura en bloques con tope;
responden con `Content-Disposition: inline` y `X-Content-Type-Options:
nosniff` (lo hace el router).
"""

import asyncio
import contextlib
import hashlib
import uuid as uuid_mod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from app.config import obtener_settings
from app.errors import ErrorDominio

PNG = ("image/png", ".png")
JPG = ("image/jpeg", ".jpg")
PDF = ("application/pdf", ".pdf")

# Firmas binarias por formato admitido (sniffing, nunca la extensión).
FIRMAS: dict[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "pdf": (b"%PDF-",),
}

_MEDIA_POR_FORMATO = {"png": PNG, "jpg": JPG, "pdf": PDF}


class ErrorArchivo(ErrorDominio):
    """El archivo no cumple lo que el punto de subida exige."""


@dataclass(frozen=True)
class Archivo:
    """Contenido validado: bytes, tipo MIME y extensión segura."""

    contenido: bytes
    media_type: str
    extension: str


def sniff_formato(datos: bytes) -> str | None:
    """Identifica el formato por la firma al inicio del archivo; None si es otro."""
    for formato, firmas in FIRMAS.items():
        if any(datos.startswith(firma) for firma in firmas):
            return formato
    return None


def validar(
    datos: bytes,
    *,
    uso: str,
    formatos: tuple[str, ...],
    maximo_bytes: int,
) -> Archivo:
    """Valida longitud y firma binaria; devuelve bytes con su tipo seguro.

    `uso` solo precisa el mensaje ('logotipo', 'documento').
    """
    if not datos:
        raise ErrorArchivo(422, "ARCHIVO_VACIO", f"El {uso} está vacío o no se recibió.")
    if len(datos) > maximo_bytes:
        raise ErrorArchivo(
            422,
            "ARCHIVO_MUY_GRANDE",
            f"El {uso} excede el tamaño máximo permitido.",
        )
    formato = sniff_formato(datos)
    if formato not in formatos:
        permitidos = " o ".join(sorted(formatos))
        raise ErrorArchivo(
            422,
            "FORMATO_INVALIDO",
            f"El {uso} debe ser {permitidos} y se valida por su contenido real.",
        )
    media, extension = _MEDIA_POR_FORMATO[formato]
    return Archivo(datos, media, extension)


@dataclass(frozen=True)
class DocumentoGuardado:
    """Metadatos de un documento privado ya escrito en el almacén."""

    path_relativo: str  # p. ej. 'ordenes/2026/1a2b3c.png'
    media_type: str
    tamano: int
    hash_sha256: str


def _destino_orden(anio: int, extension: str) -> Path:
    base = Path(obtener_settings().almacenamiento_dir) / "ordenes" / str(anio)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid_mod.uuid4().hex}{extension}"


async def guardar_documento_orden(datos: bytes, extension: str, anio: int) -> DocumentoGuardado:
    """ORD-03: guarda el documento en `almacenamiento/ordenes/{año}/` de forma privada.

    Devuelve los metadatos que quedan en la fila de la orden (ruta relativa a
    `almacenamiento/`, tipo MIME real, tamaño y hash).
    """
    destino = _destino_orden(anio, extension)
    # La E/S de disco va fuera del bucle de eventos; nunca bloquea la API.
    await asyncio.to_thread(destino.write_bytes, datos)
    return DocumentoGuardado(
        path_relativo=str(destino.relative_to(obtener_settings().almacenamiento_dir)),
        media_type=_MEDIA_POR_FORMATO[sniff_formato(datos)][0],
        tamano=len(datos),
        hash_sha256=hashlib.sha256(datos).hexdigest(),
    )


async def eliminar_documento(path_relativo: str) -> None:
    """ORD-03: retira del almacén un documento que dejó de estar referenciado.

    No falla si el archivo ya no existe: el estado de la base manda.
    """
    ruta = Path(obtener_settings().almacenamiento_dir) / path_relativo

    def _quitar() -> None:
        with contextlib.suppress(FileNotFoundError):
            ruta.unlink()

    await asyncio.to_thread(_quitar)


BLOQUE_LECTURA = 1 * 1024 * 1024  # ORD-03: la descarga se lee en bloques con tope.


async def leer_bloques(path_relativo: str, fuente_verificada: str) -> AsyncIterator[bytes]:
    """ORD-04: sirve un documento leyendo en bloques, nunca el archivo entero en RAM.

    `fuente_verificada` es el hash esperado: si el archivo en disco cambió,
    se corta la descarga a mitad de flujo en lugar de entregar bytes ajenos.
    """
    ruta = Path(obtener_settings().almacenamiento_dir) / path_relativo
    hash_calculado = hashlib.sha256()
    handle = await asyncio.to_thread(ruta.open, "rb")
    try:
        while True:
            bloque = await asyncio.to_thread(handle.read, BLOQUE_LECTURA)
            if not bloque:
                break
            hash_calculado.update(bloque)
            yield bloque
    finally:
        await asyncio.to_thread(handle.close)
    if hash_calculado.hexdigest() != fuente_verificada:
        raise ErrorArchivo(
            409, "ARCHIVO_CORRUPTO", "El documento ya no coincide con su registro."
        )

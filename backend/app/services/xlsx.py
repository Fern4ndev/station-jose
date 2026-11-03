"""Generación en memoria de libros XLSX para exportaciones de reportes."""

from collections.abc import Sequence
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font


def crear(nombre_hoja: str, columnas: Sequence[str], filas: Sequence[dict[str, Any]]) -> bytes:
    """Escribe encabezados y filas con openpyxl, sin archivos temporales."""
    libro = Workbook(write_only=False)
    hoja = libro.active
    hoja.title = nombre_hoja[:31]
    hoja.append(list(columnas))
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for fila in filas:
        hoja.append([fila.get(columna) for columna in columnas])
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()

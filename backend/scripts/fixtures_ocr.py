"""Genera los documentos de prueba del OCR (Fase 9) en `tests/fixtures/`.

Los dos archivos que exige la verificación de la fase:
- `oc_digital.pdf`: una orden de compra con texto digital (Helvetica; el
  lector debe tomarlo por texto_digital con pdfplumber).
- `oc_foto.jpg`: la misma orden tendida en imagen (la que saldría de una
  cámara o un escáner; el lector debe renderizarla/leerla por OCR).

Ambos usan datos ficticios (`INSTITUCION DEMO DEL SUR S.A.C.`), sin datos
reales de ninguna institución. Regenerar:

    python scripts/fixtures_ocr.py
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "tests" / "fixtures"

# Campos de la extracción del plan: número, fecha, monto y señores.
RENGLEMS = (
    "SEÑORES: INSTITUCION DEMO DEL SUR S.A.C.",
    "ORDEN DE COMPRA N° 0018-2026",
    "FECHA: 15/03/2027",
    "MONTO: S/ 1,500.00",
)


def generar_pdf(ruta: Path) -> None:
    """Orden de compra con texto digital, con la librería reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    alto, ancho = A4  # reportlab da (x, y): 595 x 842
    lienzo = canvas.Canvas(str(ruta), pagesize=(ancho, alto))
    y = alto - 100
    for texto in RENGLEMS:
        lienzo.setFont("Helvetica", 16)
        lienzo.drawString(70, y, texto)
        y -= 60
    lienzo.save()


def generar_foto(ruta: Path, desde_pdf: Path) -> None:
    """Foto de la orden: página del PDF tendida a imagen y pasada a JPG."""
    import pypdfium2 as pdfium
    from app.services.ocr.preprocesado import Pasos, preparar

    documento = pdfium.PdfDocument(desde_pdf.read_bytes())
    try:
        pagina = documento[0]
        bitmap = pagina.render(scale=200 / 72)
        matriz = bitmap.to_numpy()
        if matriz.ndim == 3 and matriz.shape[2] == 4:
            matriz = matriz[:, :, :3]
        pagina.close()
    finally:
        documento.close()
    # La foto 'de cámara' pasa por el preprocesado real del pipeline para que
    # el motor vea lo mismo que verá en producción.
    preparada = preparar(matriz, Pasos())
    cv2.imwrite(str(ruta), preparada, [cv2.IMWRITE_JPEG_QUALITY, 92])


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    pdf = DESTINO / "oc_digital.pdf"
    foto = DESTINO / "oc_foto.jpg"
    generar_pdf(pdf)
    generar_foto(foto, pdf)
    print(f"OK: {pdf.name} y {foto.name} regenerados en {DESTINO}.")


if __name__ == "__main__":
    main()

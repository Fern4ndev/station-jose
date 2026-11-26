"""OCR service safety and field extraction tests."""

from types import SimpleNamespace

import fitz
import pytest
from app.core.config import Settings
from app.core.exceptions import InvalidPdfError
from app.services.ocr_service import OcrService, _extract_fields


def test_rejects_non_pdf_content(tmp_path) -> None:
    settings = Settings(OCR_TEMP_DIR=str(tmp_path))

    with pytest.raises(InvalidPdfError):
        OcrService(settings).preview(
            b"not a pdf",
            filename="document.txt",
            content_type="text/plain",
        )


def test_extracts_labeled_purchase_order_fields() -> None:
    fields = _extract_fields(
        """Número de orden: OC-001
SIAF: 12345
Fecha de emisión: 15/02/2026
Entidad: Municipalidad de Prueba
Proveedor: Estación San José
Unidad Ejecutora: Abastecimiento
RUC de la unidad ejecutora: 20123456789
"""
    )

    assert fields.order_number == "OC-001"
    assert fields.siaf_number == "12345"
    assert fields.issue_date is not None
    assert fields.executing_unit_ruc == "20123456789"


def test_preview_reads_a_real_pdf_and_requires_manual_review(tmp_path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Numero de orden: OC-123\nSIAF: 5678\nEntidad: Entidad de prueba")
    pdf = document.tobytes()
    document.close()
    result = OcrService(Settings(OCR_TEMP_DIR=str(tmp_path))).preview(
        pdf, filename="orden.pdf", content_type="application/pdf"
    )
    assert result.fields.order_number == "OC-123"
    assert result.fields.siaf_number == "5678"
    assert result.requires_manual_review is True
    assert not list(tmp_path.iterdir())


def test_rejects_pdf_exceeding_configured_size(tmp_path) -> None:
    service = OcrService(Settings(OCR_TEMP_DIR=str(tmp_path), OCR_MAX_UPLOAD_BYTES=8))
    with pytest.raises(InvalidPdfError):
        service.preview(
            b"%PDF-more-than-eight-bytes", filename="orden.pdf", content_type="application/pdf"
        )


@pytest.mark.parametrize("texts", [("Numero de orden: OC-123", "SIAF: 5678"), None])
def test_reads_current_rapidocr_output(texts) -> None:
    service = OcrService(Settings())
    with fitz.open() as document:
        page = document.new_page()
        text = service._ocr_page(page, lambda image: SimpleNamespace(txts=texts))

    assert text == "\n".join(texts or ())


def test_preview_reads_all_three_pages(tmp_path) -> None:
    with fitz.open() as document:
        for number in range(1, 4):
            page = document.new_page()
            page.insert_text((72, 72), f"Pagina {number}")
        content = document.tobytes()

    preview = OcrService(Settings(_env_file=None, OCR_TEMP_DIR=str(tmp_path))).preview(
        content, filename="three-pages.pdf", content_type="application/pdf"
    )

    assert preview.pages_processed == 3
    assert all(f"Pagina {number}" in preview.extracted_text for number in range(1, 4))
    assert not list(tmp_path.iterdir())


def test_preview_rejects_four_pages_and_cleans_temporary_file(tmp_path) -> None:
    with fitz.open() as document:
        for _ in range(4):
            page = document.new_page()
            page.insert_text((72, 72), "Documento de cuatro paginas")
        content = document.tobytes()

    with pytest.raises(InvalidPdfError, match="3 páginas"):
        OcrService(Settings(_env_file=None, OCR_TEMP_DIR=str(tmp_path))).preview(
            content, filename="four-pages.pdf", content_type="application/pdf"
        )

    assert not list(tmp_path.iterdir())

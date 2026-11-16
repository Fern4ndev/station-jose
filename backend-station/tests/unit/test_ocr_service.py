"""OCR service safety and field extraction tests."""

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

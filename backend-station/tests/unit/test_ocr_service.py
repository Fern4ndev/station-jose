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


def test_extracts_siga_boxed_numbers_and_institution_ruc() -> None:
    fields = _extract_fields(
        """ORDEN DE COMPRA - GUÍA DE INTERNAMIENTO N°
0000101
N° Exp. SIAF :
0000000570
UNIDAD EJECUTORA : 005 MUNICIPALIDAD DE PRUEBA
NRO. IDENTIFICACIÓN : 300255
RUC: 20485584880 Teléfono: 983701058
Facturar a nombre de:
MUNICIPALIDAD DE PRUEBA
RUC:
20123456789
"""
    )
    assert fields.order_number == "0000101"
    assert fields.siaf_number == "0000000570"
    assert fields.institution_name == "MUNICIPALIDAD DE PRUEBA"
    assert fields.executing_unit_ruc == "20123456789"


def test_institution_uses_executing_unit_and_excludes_station_ruc() -> None:
    fields = _extract_fields(
        "Entidad: Nombre genérico\nUnidad ejecutora:\n005 MUNICIPALIDAD DE PRUEBA\n"
        "RUC de la unidad ejecutora: 20485584880\nRUC: 20485584880"
    )
    assert fields.institution_name == "MUNICIPALIDAD DE PRUEBA"
    assert fields.executing_unit_ruc is None


def test_ambiguous_unlabeled_institution_rucs_require_manual_review() -> None:
    fields = _extract_fields("RUC: 20485584880\nRUC: 20123456789\nRUC: 20987654321")
    assert fields.executing_unit_ruc is None


def test_reads_billing_ruc_when_ocr_misreads_its_label() -> None:
    fields = _extract_fields(
        "RUC: 20485584880\nFacturar a nombre de:\nMUNICIPALIDAD DE PRUEBA\n"
        "RUÇ : .\n20123456789\nELABORADO POR\nRUC: 20987654321"
    )
    assert fields.executing_unit_ruc == "20123456789"


_SIGA_HEADER = (
    "ORDEN DE COMPRA - GUÍA DE INTERNAMIENTO N°\n0000101\n"
    "N° Exp. SIAF: 0000000570\nUNIDAD EJECUTORA: 005 MUNICIPALIDAD DE PRUEBA"
)
_SIGA_BILLING = "Facturar a nombre de:\nMUNICIPALIDAD DE PRUEBA\nRUC: 20123456789"


def test_siga_fast_scan_reads_all_three_pages_without_full_page_ocr(tmp_path, monkeypatch) -> None:
    responses = iter([_SIGA_HEADER, _SIGA_BILLING] * 3)
    image_heights = []

    def engine(image):
        image_heights.append(image.shape[0])
        return SimpleNamespace(txts=tuple(next(responses).splitlines()))

    service = OcrService(Settings(_env_file=None, OCR_TEMP_DIR=str(tmp_path)))
    monkeypatch.setattr(service, "_create_ocr_engine", lambda: engine)
    with fitz.open() as document:
        for _ in range(3):
            document.new_page(width=600, height=840)
        content = document.tobytes()

    preview = service.preview(content, filename="siga.pdf", content_type="application/pdf")

    assert preview.pages_processed == 3
    assert preview.fields.order_number == "0000101"
    assert preview.fields.siaf_number == "0000000570"
    assert preview.fields.institution_name == "MUNICIPALIDAD DE PRUEBA"
    assert preview.fields.executing_unit_ruc == "20123456789"
    assert len(image_heights) == 6
    assert max(image_heights) < 840
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("header", ["Otro formato de orden", _SIGA_HEADER])
def test_fast_scan_falls_back_to_full_page_when_fields_are_missing(tmp_path, monkeypatch, header):
    responses = [header]
    if header == _SIGA_HEADER:
        responses.append("Facturar a nombre de:\nRUC: 20485584880")
    responses.append(f"{_SIGA_HEADER}\n{_SIGA_BILLING}")
    pending = iter(responses)
    image_heights = []

    def engine(image):
        image_heights.append(image.shape[0])
        return SimpleNamespace(txts=tuple(next(pending).splitlines()))

    service = OcrService(Settings(_env_file=None, OCR_TEMP_DIR=str(tmp_path)))
    monkeypatch.setattr(service, "_create_ocr_engine", lambda: engine)
    with fitz.open() as document:
        document.new_page(width=600, height=840)
        content = document.tobytes()

    preview = service.preview(content, filename="other-layout.pdf", content_type="application/pdf")

    assert preview.fields.executing_unit_ruc == "20123456789"
    assert len(image_heights) == len(responses)
    assert image_heights[-1] == 1680
    assert not list(tmp_path.iterdir())

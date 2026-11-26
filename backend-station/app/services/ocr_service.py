"""Temporary OCR preview processing for purchase-order PDFs."""

import re
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.exceptions import (
    InvalidPdfError,
    OcrDisabledError,
    OcrProcessingError,
    OcrTimeoutError,
)
from app.schemas.ocr import PurchaseOrderOcrFields, PurchaseOrderOcrPreview


class OcrService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def preview(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str,
    ) -> PurchaseOrderOcrPreview:
        if not self.settings.OCR_ENABLED:
            raise OcrDisabledError("El procesamiento OCR está deshabilitado.")
        if not content or not content.startswith(b"%PDF"):
            raise InvalidPdfError("El archivo debe ser un PDF válido.")
        if len(content) > self.settings.OCR_MAX_UPLOAD_BYTES:
            raise InvalidPdfError("El PDF supera el tamaño máximo permitido.")

        temp_dir = Path(self.settings.OCR_TEMP_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        started_at = time.monotonic()
        try:
            with tempfile.NamedTemporaryFile(
                dir=temp_dir, suffix=".pdf", prefix="purchase-order-", delete=False
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            return self._process_pdf(
                temporary_path,
                filename=filename or "purchase-order.pdf",
                content_type=content_type,
                started_at=started_at,
            )
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _process_pdf(
        self,
        path: Path,
        *,
        filename: str,
        content_type: str,
        started_at: float,
    ) -> PurchaseOrderOcrPreview:
        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError as exc:
            raise OcrProcessingError("El procesamiento PDF requiere instalar PyMuPDF.") from exc
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise InvalidPdfError("No se pudo abrir el PDF recibido.") from exc
        try:
            if document.page_count > self.settings.OCR_MAX_PDF_PAGES:
                raise InvalidPdfError(
                    f"El PDF debe tener como máximo {self.settings.OCR_MAX_PDF_PAGES} páginas."
                )
            text_pages: list[str] = []
            warnings: list[str] = []
            ocr_engine: Any = None
            for page_number, page in enumerate(document, start=1):
                self._check_timeout(started_at)
                page_text = page.get_text("text").strip()
                if not page_text:
                    if ocr_engine is None:
                        ocr_engine = self._create_ocr_engine()
                    page_text = self._ocr_page(page, ocr_engine)
                    self._check_timeout(started_at)
                    if page_text:
                        warnings.append(f"La página {page_number} fue procesada mediante OCR.")
                    else:
                        warnings.append(f"No se pudo extraer texto de la página {page_number}.")
                text_pages.append(page_text)
            extracted_text = "\n\n".join(text_pages).strip()
            fields = _extract_fields(extracted_text)
            return PurchaseOrderOcrPreview(
                filename=filename,
                content_type=content_type or "application/pdf",
                pages_processed=document.page_count,
                extracted_text=extracted_text,
                fields=fields,
                unrecognized_fields=_unrecognized_fields(fields),
                warnings=warnings,
            )
        except (InvalidPdfError, OcrTimeoutError, OcrProcessingError):
            raise
        except Exception as exc:
            raise OcrProcessingError("Ocurrió un error al procesar el PDF.") from exc
        finally:
            document.close()

    def _create_ocr_engine(self) -> Any:
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise OcrProcessingError("El OCR requiere instalar RapidOCR y ONNX Runtime.") from exc
        return RapidOCR()

    def _ocr_page(self, page: Any, engine: Any) -> str:
        try:
            import fitz
            import numpy as np

            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            result = engine(image)
            return "\n".join(text.strip() for text in (result.txts or ()) if text.strip())
        except Exception as exc:
            raise OcrProcessingError("RapidOCR no pudo procesar una página.") from exc

    def _check_timeout(self, started_at: float) -> None:
        if time.monotonic() - started_at > self.settings.OCR_TIMEOUT_SECONDS:
            raise OcrTimeoutError("El procesamiento OCR excedió el tiempo máximo permitido.")


def _extract_fields(text: str) -> PurchaseOrderOcrFields:
    return PurchaseOrderOcrFields(
        order_number=_label_value(
            text, r"(?:n[úu]mero\s+de\s+orden|orden\s+de\s+compra|n[.º°]\s*de\s*orden)"
        ),
        siaf_number=_label_value(text, r"(?:siaf|expediente\s+siaf)"),
        issue_date=_extract_date(text),
        institution_name=_label_value(text, r"(?:entidad|instituci[oó]n)"),
        supplier_name=_label_value(text, r"(?:proveedor)"),
        executing_unit=_label_value(text, r"(?:unidad\s+ejecutora)"),
        executing_unit_ruc=_label_value(text, r"(?:ruc\s+(?:de\s+la\s+)?unidad\s+ejecutora)"),
    )


def _label_value(text: str, label_pattern: str) -> str | None:
    pattern = re.compile(rf"{label_pattern}\s*[:#-]?\s*(.+)", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.search(line.strip())
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
            if value:
                return value
    return None


def _extract_date(text: str) -> date | None:
    value = _label_value(text, r"(?:fecha\s+de\s+emisi[oó]n|fecha)")
    candidates = [value] if value else []
    candidates.extend(re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", text))
    candidates.extend(re.findall(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b", text))
    for candidate in candidates:
        if not candidate:
            continue
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(candidate.strip(), pattern).date()
            except ValueError:
                continue
    return None


def _unrecognized_fields(fields: PurchaseOrderOcrFields) -> list[str]:
    values = fields.model_dump()
    return [name for name, value in values.items() if value is None or value == []]

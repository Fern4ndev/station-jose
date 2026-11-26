"""Temporary OCR preview processing for purchase-order PDFs."""

import re
import tempfile
import time
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import Settings
from app.core.exceptions import (
    InvalidPdfError,
    OcrDisabledError,
    OcrProcessingError,
    OcrTimeoutError,
)
from app.schemas.ocr import PurchaseOrderOcrFields, PurchaseOrderOcrPreview

_OCR_LOCK = Lock()
_STATION_RUC = "20485584880"


@lru_cache(maxsize=1)
def _load_ocr_engine() -> Any:
    try:
        from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
    except ImportError as exc:
        raise OcrProcessingError("El OCR requiere instalar RapidOCR y ONNX Runtime.") from exc
    return RapidOCR(
        params={
            "EngineConfig.onnxruntime.intra_op_num_threads": 2,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            "Det.ocr_version": OCRVersion.PPOCRV4,
            "Det.model_type": ModelType.MOBILE,
            "Det.limit_type": "max",
            "Det.limit_side_len": 1280,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
            "Rec.model_type": ModelType.MOBILE,
            "Rec.lang_type": LangRec.LATIN,
        }
    )


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
                    page_text = self._read_scanned_page(page, ocr_engine, started_at=started_at)
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
        return _load_ocr_engine()

    def _read_scanned_page(self, page: Any, engine: Any, *, started_at: float) -> str:
        import fitz

        rect = page.rect
        header = self._ocr_page(
            page,
            engine,
            started_at=started_at,
            clip=fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * 0.245),
        )
        self._check_timeout(started_at)
        header_fields = _extract_fields(header)
        if (
            re.search(r"gu[íi]a\s+de\s+internamiento", header, re.IGNORECASE)
            and header_fields.order_number
            and header_fields.siaf_number
            and header_fields.executing_unit
        ):
            billing = self._ocr_page(
                page,
                engine,
                started_at=started_at,
                clip=fitz.Rect(
                    rect.x0, rect.y0 + rect.height * 0.73, rect.x1, rect.y0 + rect.height * 0.84
                ),
            )
            self._check_timeout(started_at)
            selected_text = f"{header}\n\n{billing}"
            if _extract_fields(selected_text).executing_unit_ruc:
                return selected_text
        return self._ocr_page(page, engine, started_at=started_at)

    def _ocr_page(
        self, page: Any, engine: Any, *, started_at: float | None = None, clip: Any = None
    ) -> str:
        try:
            import fitz
            import numpy as np

            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False, clip=clip)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            remaining = float(self.settings.OCR_TIMEOUT_SECONDS)
            if started_at is not None:
                remaining -= time.monotonic() - started_at
            if not _OCR_LOCK.acquire(timeout=max(0, remaining)):
                raise OcrTimeoutError("El procesamiento OCR excedió el tiempo máximo permitido.")
            try:
                result = engine(image)
            finally:
                _OCR_LOCK.release()
            return "\n".join(text.strip() for text in (result.txts or ()) if text.strip())
        except OcrTimeoutError:
            raise
        except Exception as exc:
            raise OcrProcessingError("RapidOCR no pudo procesar una página.") from exc

    def _check_timeout(self, started_at: float) -> None:
        if time.monotonic() - started_at > self.settings.OCR_TIMEOUT_SECONDS:
            raise OcrTimeoutError("El procesamiento OCR excedió el tiempo máximo permitido.")


def _extract_fields(text: str) -> PurchaseOrderOcrFields:
    executing_unit = _label_value(text, r"unidad\s+ejecutora")
    if executing_unit:
        executing_unit = re.sub(r"^\d+\s+", "", executing_unit)
    return PurchaseOrderOcrFields(
        order_number=_labeled_number(
            text,
            r"(?:n[úu]mero\s+de\s+orden|orden\s+de\s+compra"
            r"(?:\s*[-–]\s*gu[íi]a\s+de\s+internamiento)?|n[.º°]\s*de\s*orden)",
        ),
        siaf_number=_labeled_number(text, r"siaf"),
        issue_date=_extract_date(text),
        institution_name=executing_unit or _label_value(text, r"(?:entidad|instituci[oó]n)"),
        supplier_name=_label_value(text, r"(?:proveedor|se[ñn]or\(es\))"),
        executing_unit=executing_unit,
        executing_unit_ruc=_institution_ruc(text),
    )


def _labeled_number(text: str, label_pattern: str) -> str | None:
    match = re.search(
        rf"\b{label_pattern}\s*(?:n[.º°o]\s*)?[:#-]?\s*([a-z]+-\d[\w./-]*|\d[\d./-]*)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _institution_ruc(text: str) -> str | None:
    explicit = _label_value(text, r"ruc\s+(?:de\s+la\s+)?unidad\s+ejecutora")
    if explicit:
        match = re.search(r"\b\d{11}\b", explicit)
        if match and match.group() != _STATION_RUC:
            return match.group()
    billing_rucs = {
        ruc.group()
        for section in re.finditer(
            r"facturar?\s+a\s+nombre\s+de.*?(?=elaborado\s+por|nota\s+importante|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for ruc in re.finditer(r"\b\d{11}\b", section.group())
    } - {_STATION_RUC}
    if billing_rucs:
        return billing_rucs.pop() if len(billing_rucs) == 1 else None
    candidates = {
        re.sub(r"\s", "", match.group(1))
        for match in re.finditer(
            r"\br\.?\s*u\.?\s*c\.?\s*[:#-]?\s*(\d(?:[ \t]*\d){10})\b",
            text,
            re.IGNORECASE,
        )
    } - {_STATION_RUC}
    return candidates.pop() if len(candidates) == 1 else None


def _label_value(text: str, label_pattern: str) -> str | None:
    pattern = re.compile(
        rf"^(?:{label_pattern})(?=[ \t:#-]|$)[ \t]*[:#-]?[ \t]*(.*)", re.IGNORECASE
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
            if not value and index + 1 < len(lines):
                value = lines[index + 1]
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

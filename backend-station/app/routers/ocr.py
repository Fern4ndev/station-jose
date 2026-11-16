"""OCR preview endpoint for purchase-order PDFs."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import Settings, get_settings
from app.core.dependencies import require_permission
from app.schemas.ocr import PurchaseOrderOcrPreview
from app.services.ocr_service import OcrService

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post(
    "/purchase-order-previews",
    response_model=PurchaseOrderOcrPreview,
    dependencies=[Depends(require_permission("ocr.purchase_orders.process"))],
)
def create_purchase_order_preview(
    file: Annotated[UploadFile, File(description="PDF de la orden de compra")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PurchaseOrderOcrPreview:
    content = file.file.read(settings.OCR_MAX_UPLOAD_BYTES + 1)
    return OcrService(settings).preview(
        content,
        filename=file.filename or "purchase-order.pdf",
        content_type=file.content_type or "application/pdf",
    )

"""OCR preview schemas for purchase orders."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class OcrLineCandidate(BaseModel):
    fuel_description: str | None = None
    authorized_gallons: Decimal | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None


class PurchaseOrderOcrFields(BaseModel):
    order_number: str | None = None
    siaf_number: str | None = None
    issue_date: date | None = None
    institution_name: str | None = None
    supplier_name: str | None = None
    executing_unit: str | None = None
    executing_unit_ruc: str | None = None
    lines: list[OcrLineCandidate] = Field(default_factory=list)


class PurchaseOrderOcrPreview(BaseModel):
    filename: str
    content_type: str
    pages_processed: int
    extracted_text: str
    fields: PurchaseOrderOcrFields
    unrecognized_fields: list[str]
    warnings: list[str]
    requires_manual_review: bool = True

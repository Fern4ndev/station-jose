"""Voucher query and correction schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.attendance import VoucherResponse
from app.schemas.purchase_order import PaginationResponse


class VoucherListResponse(BaseModel):
    items: list[VoucherResponse]
    pagination: PaginationResponse


class VoucherFilters(BaseModel):
    purchase_order_id: UUID | None = None
    voucher_number: str | None = None
    issuer_name: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class VoucherDescriptiveUpdate(BaseModel):
    issuer_type: str | None = Field(default=None, pattern="^(INSTITUTION|STATION)$")
    issuer_name: str | None = Field(default=None, min_length=1, max_length=200)
    voucher_number: str | None = Field(default=None, min_length=1, max_length=60)

    @model_validator(mode="after")
    def require_change(self) -> "VoucherDescriptiveUpdate":
        if all(
            value is None for value in (self.issuer_type, self.issuer_name, self.voucher_number)
        ):
            raise ValueError("Debe indicar al menos un dato descriptivo para corregir.")
        return self

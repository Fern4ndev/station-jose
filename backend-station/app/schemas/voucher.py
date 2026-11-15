"""Voucher query schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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

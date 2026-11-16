"""Attendance request and response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.verification import VerificationResponse


class AttendanceItemCreate(BaseModel):
    purchase_order_item_id: UUID | None = None
    voucher_item_id: UUID | None = None
    attended_gallons: Decimal = Field(gt=0, max_digits=14, decimal_places=3)

    @model_validator(mode="after")
    def validate_reference(self) -> "AttendanceItemCreate":
        if (self.purchase_order_item_id is None) == (self.voucher_item_id is None):
            raise ValueError("Debe indicar exactamente una línea de orden o una línea de vale.")
        return self


class AttendanceCreate(BaseModel):
    items: list[AttendanceItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distinct_items(self) -> "AttendanceCreate":
        references = [item.voucher_item_id or item.purchase_order_item_id for item in self.items]
        if len(references) != len(set(references)):
            raise ValueError("Cada línea de combustible solo puede aparecer una vez.")
        return self


class FirstAttendanceCreate(AttendanceCreate):
    issuer_type: str = Field(pattern="^(INSTITUTION|STATION)$")
    issuer_name: str = Field(min_length=1, max_length=200)
    voucher_number: str = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def validate_order_items(self) -> "FirstAttendanceCreate":
        order_ids = [item.purchase_order_item_id for item in self.items]
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("Cada línea de combustible solo puede aparecer una vez.")
        if any(item.voucher_item_id is not None for item in self.items):
            raise ValueError("La primera atención debe referenciar líneas de la orden.")
        return self


class AttendanceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    voucher_item_id: UUID
    attended_gallons: Decimal
    unit_price_snapshot: Decimal
    attended_amount: Decimal


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    voucher_id: UUID
    performed_by_user_id: UUID
    branch_id: UUID
    attended_at: datetime
    idempotency_key: UUID
    items: list[AttendanceItemResponse]
    verifications: list[VerificationResponse] = Field(default_factory=list)


class VoucherResponse(BaseModel):
    id: UUID
    purchase_order_id: UUID
    issuer_type: str
    issuer_name: str
    voucher_number: str
    created_at: datetime
    status: str
    verification_status: str
    items: list["VoucherItemDetailResponse"]
    attendances: list[AttendanceResponse]


class VoucherItemDetailResponse(BaseModel):
    id: UUID
    purchase_order_item_id: UUID
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str

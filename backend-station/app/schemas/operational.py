"""Responses that exclude financial values for operational users."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.catalog import BranchResponse, FuelTypeResponse
from app.schemas.purchase_order import PaginationResponse
from app.schemas.verification import VerificationResponse


class OperationalModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OperationalOrderItem(OperationalModel):
    id: UUID
    fuel_type: FuelTypeResponse
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str


class OperationalOrder(OperationalModel):
    id: UUID
    order_number: str
    siaf_number: str
    issue_date: date
    institution_name: str
    supplier_name: str
    supplier_details: str | None
    executing_unit: str
    executing_unit_ruc: str
    branch: BranchResponse
    deleted_at: datetime | None
    items: list[OperationalOrderItem]
    status: str


class OperationalOrderList(OperationalModel):
    items: list[OperationalOrder]
    pagination: PaginationResponse


class OperationalAttendanceItem(OperationalModel):
    id: UUID
    voucher_item_id: UUID
    attended_gallons: Decimal


class OperationalAttendance(OperationalModel):
    id: UUID
    voucher_id: UUID
    performed_by_user_id: UUID
    branch_id: UUID
    attended_at: datetime
    idempotency_key: UUID
    items: list[OperationalAttendanceItem]
    verifications: list[VerificationResponse]


class OperationalVoucherItem(OperationalModel):
    id: UUID
    purchase_order_item_id: UUID
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str


class OperationalVoucher(OperationalModel):
    id: UUID
    purchase_order_id: UUID
    issuer_type: str
    issuer_name: str
    voucher_number: str
    created_at: datetime
    status: str
    verification_status: str
    items: list[OperationalVoucherItem]
    attendances: list[OperationalAttendance]


class OperationalVoucherList(OperationalModel):
    items: list[OperationalVoucher]
    pagination: PaginationResponse

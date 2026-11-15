"""Derived balance and status schemas."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class BalanceStatus(StrEnum):
    PENDING = "PENDING"
    PARTIALLY_ATTENDED = "PARTIALLY_ATTENDED"
    COMPLETED = "COMPLETED"
    BLOCKED_BY_ORDER_BALANCE = "BLOCKED_BY_ORDER_BALANCE"
    PARTIALLY_BLOCKED = "PARTIALLY_BLOCKED"


class BalanceResponse(BaseModel):
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: BalanceStatus


class VoucherItemResponse(BalanceResponse):
    id: UUID
    purchase_order_item_id: UUID
    fuel_type_id: UUID
    fuel_type_code: str
    fuel_type_name: str


class VoucherBalanceResponse(BaseModel):
    status: BalanceStatus
    items: list[VoucherItemResponse]


class OrderBalanceResponse(BalanceResponse):
    id: UUID
    fuel_type_id: UUID
    fuel_type_code: str
    fuel_type_name: str

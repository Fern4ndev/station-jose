"""Reporting request and response schemas."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ReportGrouping(StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ReportFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    user_id: UUID | None = None
    branch_id: UUID | None = None
    status: str | None = None
    group_by: ReportGrouping = ReportGrouping.DAY
    hour_from: int = Field(default=0, ge=0, le=23)
    hour_to: int = Field(default=23, ge=0, le=23)


class PurchaseOrderReportRow(BaseModel):
    order_id: UUID
    order_number: str
    institution_name: str
    branch_name: str
    issue_date: date
    fuel_type_code: str
    fuel_type_name: str
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str
    unit_price: Decimal
    total_amount: Decimal


class PurchaseOrderReportResponse(BaseModel):
    generated_at: datetime
    filters: ReportFilters
    items: list[PurchaseOrderReportRow]
    total: int


class AttendanceReportRow(BaseModel):
    attendance_id: UUID
    voucher_id: UUID
    voucher_number: str
    order_id: UUID
    order_number: str
    attended_at: datetime
    performed_by_user_id: UUID
    performer_name: str
    branch_name: str
    fuel_type_code: str
    fuel_type_name: str
    attended_gallons: Decimal
    unit_price: Decimal
    attended_amount: Decimal


class AttendanceReportResponse(BaseModel):
    generated_at: datetime
    filters: ReportFilters
    items: list[AttendanceReportRow]
    total: int


class FuelDashboardRow(BaseModel):
    fuel_type_code: str
    fuel_type_name: str
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    attended_amount: Decimal


class PeriodDashboardRow(BaseModel):
    period: str
    attended_gallons: Decimal
    attended_amount: Decimal
    attendances: int


class DashboardResponse(BaseModel):
    generated_at: datetime
    filters: ReportFilters
    orders: int
    vouchers: int
    attendances: int
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    attended_amount: Decimal
    by_fuel: list[FuelDashboardRow]
    by_period: list[PeriodDashboardRow]

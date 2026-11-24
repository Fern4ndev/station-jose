"""Read-only report queries."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.tables import (
    Attendance,
    AttendanceItem,
    PurchaseOrder,
    PurchaseOrderItem,
    VoucherItem,
)


class ReportRepository:
    def list_purchase_orders(
        self,
        db: Session,
        *,
        date_from: date | None,
        date_to: date | None,
        branch_id: UUID | None,
    ) -> list[PurchaseOrder]:
        filters: list[ColumnElement[bool]] = [PurchaseOrder.deleted_at.is_(None)]
        if date_from is not None:
            filters.append(PurchaseOrder.issue_date >= date_from)
        if date_to is not None:
            filters.append(PurchaseOrder.issue_date <= date_to)
        if branch_id is not None:
            filters.append(PurchaseOrder.branch_id == branch_id)
        statement = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.branch),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.fuel_type),
            )
            .where(*filters)
            .order_by(PurchaseOrder.issue_date.desc(), PurchaseOrder.order_number)
        )
        return list(db.scalars(statement).unique())

    def list_attendances(
        self,
        db: Session,
        *,
        date_from: date | None,
        date_to: date | None,
        user_id: UUID | None,
        branch_id: UUID | None,
    ) -> list[Attendance]:
        filters: list[ColumnElement[bool]] = []
        if date_from is not None:
            filters.append(Attendance.attended_at >= _start_of_day(date_from))
        if date_to is not None:
            filters.append(Attendance.attended_at < _start_of_day(date_to + timedelta(days=1)))
        if user_id is not None:
            filters.append(Attendance.performed_by_user_id == user_id)
        if branch_id is not None:
            filters.append(Attendance.branch_id == branch_id)
        statement = (
            select(Attendance)
            .options(
                selectinload(Attendance.voucher),
                selectinload(Attendance.performed_by),
                selectinload(Attendance.branch),
                selectinload(Attendance.items)
                .selectinload(AttendanceItem.voucher_item)
                .selectinload(VoucherItem.purchase_order_item)
                .selectinload(PurchaseOrderItem.fuel_type),
                selectinload(Attendance.items)
                .selectinload(AttendanceItem.voucher_item)
                .selectinload(VoucherItem.purchase_order_item)
                .selectinload(PurchaseOrderItem.purchase_order),
            )
            .where(*filters)
            .order_by(Attendance.attended_at.desc(), Attendance.id)
        )
        return list(db.scalars(statement).unique())


def _start_of_day(value: date) -> datetime:
    business_zone = ZoneInfo(get_settings().TIMEZONE)
    return datetime.combine(value, time.min, tzinfo=business_zone).astimezone(UTC)

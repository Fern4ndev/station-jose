"""Voucher persistence queries."""

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import UnaryExpression

from app.tables import (
    Attendance,
    AttendanceItem,
    PurchaseOrder,
    PurchaseOrderItem,
    Voucher,
    VoucherItem,
)


class VoucherRepository:
    def get_by_id(
        self,
        db: Session,
        voucher_id: UUID,
        *,
        branch_id: UUID | None = None,
    ) -> Voucher | None:
        statement = (
            select(Voucher)
            .options(
                selectinload(Voucher.items).selectinload(VoucherItem.purchase_order_item),
                selectinload(Voucher.attendances).selectinload(Attendance.items),
            )
            .where(Voucher.id == voucher_id)
        )
        if branch_id is not None:
            statement = statement.join(PurchaseOrder).where(
                PurchaseOrder.branch_id == branch_id
            )
        return db.scalar(statement)

    def get_duplicate(
        self,
        db: Session,
        *,
        purchase_order_id: UUID,
        issuer_normalized: str,
        voucher_number_normalized: str,
    ) -> Voucher | None:
        return db.scalar(
            select(Voucher).where(
                Voucher.purchase_order_id == purchase_order_id,
                Voucher.issuer_normalized == issuer_normalized,
                Voucher.voucher_number_normalized == voucher_number_normalized,
            )
        )

    def lock_items(self, db: Session, item_ids: Iterable[UUID]) -> list[PurchaseOrderItem]:
        ids = sorted(set(item_ids), key=str)
        if not ids:
            return []
        statement = (
            select(PurchaseOrderItem)
            .options(
                selectinload(PurchaseOrderItem.fuel_type),
                selectinload(PurchaseOrderItem.purchase_order),
            )
            .where(PurchaseOrderItem.id.in_(ids))
            .order_by(PurchaseOrderItem.id)
            .with_for_update()
        )
        return list(db.scalars(statement))

    def order_item_ids_for_voucher(self, db: Session, voucher_id: UUID) -> list[UUID]:
        return list(
            db.scalars(
                select(VoucherItem.purchase_order_item_id).where(
                    VoucherItem.voucher_id == voucher_id
                )
            )
        )

    def lock_voucher(self, db: Session, voucher_id: UUID) -> Voucher | None:
        return db.scalar(select(Voucher).where(Voucher.id == voucher_id).with_for_update())

    def lock_voucher_items(self, db: Session, item_ids: Iterable[UUID]) -> list[VoucherItem]:
        ids = sorted(set(item_ids), key=str)
        if not ids:
            return []
        statement = (
            select(VoucherItem)
            .options(
                selectinload(VoucherItem.purchase_order_item).selectinload(
                    PurchaseOrderItem.fuel_type
                ),
                selectinload(VoucherItem.purchase_order_item).selectinload(
                    PurchaseOrderItem.purchase_order
                ),
            )
            .where(VoucherItem.id.in_(ids))
            .order_by(VoucherItem.id)
            .with_for_update()
        )
        return list(db.scalars(statement))

    def get_attendance_by_idempotency(
        self, db: Session, idempotency_key: UUID
    ) -> Attendance | None:
        return db.scalar(
            select(Attendance)
            .options(selectinload(Attendance.items))
            .where(Attendance.idempotency_key == idempotency_key)
        )

    def consumed_by_order_items(self, db: Session, item_ids: Iterable[UUID]) -> dict[UUID, object]:
        ids = list(item_ids)
        if not ids:
            return {}
        rows = db.execute(
            select(
                VoucherItem.purchase_order_item_id,
                func.coalesce(func.sum(AttendanceItem.attended_gallons), 0),
            )
            .join(AttendanceItem, AttendanceItem.voucher_item_id == VoucherItem.id)
            .where(VoucherItem.purchase_order_item_id.in_(ids))
            .group_by(VoucherItem.purchase_order_item_id)
        )
        return {item_id: consumed for item_id, consumed in rows}

    def consumed_by_voucher_items(
        self, db: Session, item_ids: Iterable[UUID]
    ) -> dict[UUID, object]:
        ids = list(item_ids)
        if not ids:
            return {}
        rows = db.execute(
            select(
                AttendanceItem.voucher_item_id,
                func.coalesce(func.sum(AttendanceItem.attended_gallons), 0),
            )
            .where(AttendanceItem.voucher_item_id.in_(ids))
            .group_by(AttendanceItem.voucher_item_id)
        )
        return {item_id: consumed for item_id, consumed in rows}

    def list(
        self,
        db: Session,
        *,
        purchase_order_id: UUID | None,
        voucher_number: str | None,
        issuer_name: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        offset: int,
        limit: int,
        attended_by_user_id: UUID | None = None,
        branch_id: UUID | None = None,
    ) -> tuple[list[Voucher], int]:
        filters = []
        if purchase_order_id is not None:
            filters.append(Voucher.purchase_order_id == purchase_order_id)
        if branch_id is not None:
            order_ids = select(PurchaseOrder.id).where(PurchaseOrder.branch_id == branch_id)
            filters.append(Voucher.purchase_order_id.in_(order_ids))
        if voucher_number:
            filters.append(
                Voucher.voucher_number_normalized.ilike(f"%{voucher_number.strip().upper()}%")
            )
        if issuer_name:
            filters.append(Voucher.issuer_normalized.ilike(f"%{issuer_name.strip().upper()}%"))
        if created_from is not None:
            filters.append(Voucher.created_at >= created_from)
        if created_to is not None:
            filters.append(Voucher.created_at <= created_to)
        ordering: tuple[UnaryExpression[datetime], ...]
        if attended_by_user_id is not None:
            attended_voucher_ids = select(Attendance.voucher_id).where(
                Attendance.performed_by_user_id == attended_by_user_id
            )
            filters.append(Voucher.id.in_(attended_voucher_ids))
        base = select(Voucher).where(*filters)
        total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
        if attended_by_user_id is not None:
            last_attended_at = (
                select(func.max(Attendance.attended_at))
                .where(
                    Attendance.voucher_id == Voucher.id,
                    Attendance.performed_by_user_id == attended_by_user_id,
                )
                .correlate(Voucher)
                .scalar_subquery()
            )
            ordering = (last_attended_at.desc(), Voucher.created_at.desc())
        else:
            ordering = (Voucher.created_at.desc(),)
        statement = (
            base.options(
                selectinload(Voucher.items).selectinload(VoucherItem.purchase_order_item),
                selectinload(Voucher.attendances).selectinload(Attendance.items),
            )
            .order_by(*ordering)
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(statement).unique()), total

"""Purchase order persistence queries."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.tables import (
    AttendanceItem,
    Branch,
    FuelType,
    PurchaseOrder,
    PurchaseOrderItem,
    VoucherItem,
)


class PurchaseOrderRepository:
    def get_by_id(
        self, db: Session, order_id: UUID, *, include_deleted: bool = False
    ) -> PurchaseOrder | None:
        statement = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.branch),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.fuel_type),
            )
            .where(PurchaseOrder.id == order_id)
        )
        if not include_deleted:
            statement = statement.where(PurchaseOrder.deleted_at.is_(None))
        return db.scalar(statement)

    def list(
        self,
        db: Session,
        *,
        search: str | None,
        branch_id: UUID | None,
        issue_date_from: date | None,
        issue_date_to: date | None,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[PurchaseOrder], int]:
        filters: list[ColumnElement[bool]] = [PurchaseOrder.deleted_at.is_(None)]
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    PurchaseOrder.order_number.ilike(pattern),
                    PurchaseOrder.institution_name.ilike(pattern),
                    PurchaseOrder.executing_unit.ilike(pattern),
                )
            )
        if branch_id is not None:
            filters.append(PurchaseOrder.branch_id == branch_id)
        if issue_date_from is not None:
            filters.append(PurchaseOrder.issue_date >= issue_date_from)
        if issue_date_to is not None:
            filters.append(PurchaseOrder.issue_date <= issue_date_to)

        base = select(PurchaseOrder).where(*filters)
        total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
        items = list(
            db.scalars(
                base.options(
                    selectinload(PurchaseOrder.branch),
                    selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.fuel_type),
                )
                .order_by(
                    (desc if sort_order == "desc" else asc)(
                        {
                            "issue_date": PurchaseOrder.issue_date,
                            "order_number": PurchaseOrder.order_number,
                            "institution_name": PurchaseOrder.institution_name,
                        }[sort_by]
                    )
                )
                .offset(offset)
                .limit(limit)
            ).unique()
        )
        return items, total

    def attended_by_order_item_ids(
        self, db: Session, item_ids: Iterable[UUID]
    ) -> dict[UUID, Decimal]:
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
        return {item_id: Decimal(str(attended or 0)) for item_id, attended in rows}

    def has_vouchers(self, db: Session, order_id: UUID) -> bool:
        return (
            db.scalar(
                select(VoucherItem.id).where(VoucherItem.purchase_order_id == order_id).limit(1)
            )
            is not None
        )

    def get_fuel_types(self, db: Session, fuel_ids: Iterable[UUID]) -> dict[UUID, FuelType]:
        ids = list(fuel_ids)
        if not ids:
            return {}
        return {fuel.id: fuel for fuel in db.scalars(select(FuelType).where(FuelType.id.in_(ids)))}

    def get_branch(self, db: Session, branch_id: UUID) -> Branch | None:
        return db.get(Branch, branch_id)

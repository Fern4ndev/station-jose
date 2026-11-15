"""Balance aggregation queries."""

from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.tables import AttendanceItem, VoucherItem


class BalanceRepository:
    def consumed_by_voucher_items(
        self, db: Session, item_ids: Iterable[UUID]
    ) -> dict[UUID, Decimal]:
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
        return {item_id: Decimal(str(consumed)) for item_id, consumed in rows}

    def consumed_by_order_items(self, db: Session, item_ids: Iterable[UUID]) -> dict[UUID, Decimal]:
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
        return {item_id: Decimal(str(consumed)) for item_id, consumed in rows}

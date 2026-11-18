"""Persistence queries for voucher corrections and deletion rules."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tables import Attendance, Voucher


class VoucherMaintenanceRepository:
    def has_attendances(self, db: Session, voucher_id: UUID) -> bool:
        return (
            db.scalar(select(Attendance.id).where(Attendance.voucher_id == voucher_id).limit(1))
            is not None
        )

    def get_voucher_for_update(self, db: Session, voucher_id: UUID) -> Voucher | None:
        return db.scalar(select(Voucher).where(Voucher.id == voucher_id).with_for_update())

    def duplicate_identity(
        self,
        db: Session,
        *,
        purchase_order_id: UUID,
        issuer_normalized: str,
        voucher_number_normalized: str,
        exclude_voucher_id: UUID,
    ) -> Voucher | None:
        return db.scalar(
            select(Voucher).where(
                Voucher.purchase_order_id == purchase_order_id,
                Voucher.issuer_normalized == issuer_normalized,
                Voucher.voucher_number_normalized == voucher_number_normalized,
                Voucher.id != exclude_voucher_id,
            )
        )

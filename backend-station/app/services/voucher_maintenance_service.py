"""Voucher descriptive correction and deletion rules."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ResourceNotFoundError,
    VoucherAlreadyExistsError,
    VoucherHasAttendancesError,
)
from app.repositories.voucher_maintenance_repository import VoucherMaintenanceRepository
from app.schemas.attendance import VoucherResponse
from app.schemas.voucher import VoucherDescriptiveUpdate
from app.services.attendance_service import AttendanceService, normalize_identity


class VoucherMaintenanceService:
    def __init__(self) -> None:
        self.vouchers = VoucherMaintenanceRepository()
        self.attendance = AttendanceService()

    def correct_voucher(
        self,
        db: Session,
        voucher_id: UUID,
        data: VoucherDescriptiveUpdate,
    ) -> VoucherResponse:
        voucher = self.vouchers.get_voucher_for_update(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")

        issuer_type = data.issuer_type or voucher.issuer_type
        issuer_name = (data.issuer_name or voucher.issuer_name).strip()
        voucher_number = (data.voucher_number or voucher.voucher_number).strip()
        issuer_normalized = normalize_identity(issuer_name)
        voucher_number_normalized = normalize_identity(voucher_number)
        duplicate = self.vouchers.duplicate_identity(
            db,
            purchase_order_id=voucher.purchase_order_id,
            issuer_normalized=issuer_normalized,
            voucher_number_normalized=voucher_number_normalized,
            exclude_voucher_id=voucher.id,
        )
        if duplicate is not None:
            raise VoucherAlreadyExistsError(
                "La corrección genera una identidad de vale duplicada.",
                details={"voucher_id": str(duplicate.id)},
            )

        voucher.issuer_type = issuer_type
        voucher.issuer_name = issuer_name
        voucher.issuer_normalized = issuer_normalized
        voucher.voucher_number = voucher_number
        voucher.voucher_number_normalized = voucher_number_normalized
        db.flush()
        return self.attendance.get_voucher(db, voucher_id)

    def delete_voucher(self, db: Session, voucher_id: UUID) -> None:
        voucher = self.vouchers.get_voucher_for_update(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")
        if self.vouchers.has_attendances(db, voucher_id):
            raise VoucherHasAttendancesError(
                "No se puede eliminar un vale que tiene atenciones registradas."
            )
        raise VoucherHasAttendancesError(
            "Los vales solo se crean junto con una atención y no tienen borrado operativo."
        )

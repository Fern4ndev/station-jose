"""Administrative verification and descriptive correction use cases."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AttendanceAlreadyVerifiedError,
    InvalidVerificationError,
    ResourceNotFoundError,
    VoucherAlreadyExistsError,
    VoucherHasAttendancesError,
)
from app.repositories.verification_repository import VerificationRepository
from app.schemas.attendance import VoucherResponse
from app.schemas.verification import (
    VerificationCreate,
    VerificationDecision,
    VerificationPendingResponse,
    VerificationResponse,
)
from app.schemas.voucher import VoucherDescriptiveUpdate
from app.services.attendance_service import AttendanceService, normalize_identity
from app.tables import Attendance


class VerificationService:
    def __init__(self) -> None:
        self.verifications = VerificationRepository()
        self.attendance = AttendanceService()

    def list_pending(self, db: Session) -> list[VerificationPendingResponse]:
        pending = self.verifications.list_pending(db)
        return [
            VerificationPendingResponse(
                attendance_id=item.id,
                voucher_id=item.voucher_id,
                purchase_order_id=item.voucher.purchase_order_id,
                voucher_number=item.voucher.voucher_number,
                issuer_name=item.voucher.issuer_name,
                performed_by_user_id=item.performed_by_user_id,
                branch_id=item.branch_id,
                attended_at=item.attended_at,
                verification_status="PENDING_VERIFICATION",
            )
            for item in pending
        ]

    def verify(
        self,
        db: Session,
        attendance_id: UUID,
        data: VerificationCreate,
        *,
        reviewer_id: UUID,
    ) -> VerificationResponse:
        attendance = self.verifications.get_attendance(db, attendance_id)
        if attendance is None:
            raise ResourceNotFoundError("Atención no encontrada.")
        if self._latest_decision(attendance) == VerificationDecision.VERIFIED:
            raise AttendanceAlreadyVerifiedError(
                "La atención ya fue verificada y no puede modificarse."
            )
        if data.decision == VerificationDecision.OBSERVED and not data.observation:
            raise InvalidVerificationError(
                "La observación es obligatoria cuando el resultado es OBSERVED."
            )
        return VerificationResponse.model_validate(
            self.verifications.add(
                db,
                attendance_id=attendance_id,
                reviewed_by_user_id=reviewer_id,
                decision=data.decision.value,
                observation=data.observation,
            ),
            from_attributes=True,
        )

    def correct_voucher(
        self,
        db: Session,
        voucher_id: UUID,
        data: VoucherDescriptiveUpdate,
    ) -> VoucherResponse:
        voucher = self.verifications.get_voucher_for_update(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")
        issuer_type = data.issuer_type or voucher.issuer_type
        issuer_name = (data.issuer_name or voucher.issuer_name).strip()
        voucher_number = (data.voucher_number or voucher.voucher_number).strip()
        issuer_normalized = normalize_identity(issuer_name)
        voucher_number_normalized = normalize_identity(voucher_number)
        duplicate = self.verifications.duplicate_identity(
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
        voucher = self.verifications.get_voucher_for_update(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")
        if self.verifications.has_attendances(db, voucher_id):
            raise VoucherHasAttendancesError(
                "No se puede eliminar un vale que tiene atenciones registradas."
            )
        raise VoucherHasAttendancesError(
            "Los vales solo se crean junto con una atención y no tienen borrado operativo."
        )

    @staticmethod
    def _latest_decision(attendance: Attendance) -> VerificationDecision | None:
        if not attendance.verifications:
            return None
        latest = max(attendance.verifications, key=lambda item: item.reviewed_at)
        return VerificationDecision(latest.decision)

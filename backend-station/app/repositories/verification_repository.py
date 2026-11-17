"""Administrative verification queries."""

from uuid import UUID, uuid4

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.tables import Attendance, AttendanceVerification, Voucher


class VerificationRepository:
    def list_pending(self, db: Session) -> list[Attendance]:
        verified = exists(
            select(AttendanceVerification.id).where(
                AttendanceVerification.attendance_id == Attendance.id,
                AttendanceVerification.decision == "VERIFIED",
            )
        )
        statement = (
            select(Attendance)
            .join(Attendance.voucher)
            .options(joinedload(Attendance.voucher), selectinload(Attendance.verifications))
            .where(~verified)
            .order_by(Attendance.attended_at.asc(), Attendance.id.asc())
        )
        return list(db.scalars(statement).unique())

    def get_attendance(self, db: Session, attendance_id: UUID) -> Attendance | None:
        return db.scalar(
            select(Attendance)
            .options(
                joinedload(Attendance.voucher),
                selectinload(Attendance.verifications),
                selectinload(Attendance.items),
            )
            .where(Attendance.id == attendance_id)
        )

    def add(
        self,
        db: Session,
        *,
        attendance_id: UUID,
        reviewed_by_user_id: UUID,
        decision: str,
        observation: str | None,
    ) -> AttendanceVerification:
        verification = AttendanceVerification(
            id=uuid4(),
            attendance_id=attendance_id,
            reviewed_by_user_id=reviewed_by_user_id,
            decision=decision,
            observation=observation,
        )
        db.add(verification)
        db.flush()
        return verification

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

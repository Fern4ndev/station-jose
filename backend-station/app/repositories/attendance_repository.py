"""Attendance persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.tables import Attendance


class AttendanceRepository:
    def get_by_id(self, db: Session, attendance_id: UUID) -> Attendance | None:
        return db.scalar(
            select(Attendance)
            .options(selectinload(Attendance.items))
            .where(Attendance.id == attendance_id)
        )

"""Attendance persistence operations."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.tables import Attendance


class AttendanceRepository:
    def list(
        self,
        db: Session,
        *,
        user_id: UUID | None,
        branch_id: UUID | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Attendance], int]:
        filters = []
        if user_id is not None:
            filters.append(Attendance.performed_by_user_id == user_id)
        if branch_id is not None:
            filters.append(Attendance.branch_id == branch_id)
        total = int(db.scalar(select(func.count(Attendance.id)).where(*filters)) or 0)
        items = list(db.scalars(
            select(Attendance)
            .options(selectinload(Attendance.items))
            .where(*filters)
            .order_by(Attendance.attended_at.desc(), Attendance.id.desc())
            .offset(offset)
            .limit(limit)
        ))
        return items, total

    def get_by_id(self, db: Session, attendance_id: UUID) -> Attendance | None:
        return db.scalar(
            select(Attendance)
            .options(selectinload(Attendance.items))
            .where(Attendance.id == attendance_id)
        )

"""User persistence operations."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.tables import User


class UserRepository:
    def get_by_id(self, db: Session, user_id: UUID) -> User | None:
        return db.scalar(select(User).options(joinedload(User.branch)).where(User.id == user_id))

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.scalar(select(User).options(joinedload(User.branch)).where(User.email == email.lower()))

    def get_by_dni(self, db: Session, dni: str) -> User | None:
        return db.scalar(select(User).where(User.dni == dni))

    def count_active_admins(self, db: Session) -> int:
        return int(db.scalar(select(func.count(User.id)).where(User.role == "ADMIN", User.is_active.is_(True))) or 0)

    def list(self, db: Session, *, offset: int, limit: int) -> tuple[list[User], int]:
        total = int(db.scalar(select(func.count(User.id))) or 0)
        items = list(
            db.scalars(
                select(User)
                .options(joinedload(User.branch))
                .order_by(User.last_name, User.first_name)
                .offset(offset)
                .limit(limit)
            ).unique()
        )
        return items, total

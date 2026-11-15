"""Branch persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tables import Branch


class BranchRepository:
    def get_by_id(self, db: Session, branch_id: UUID) -> Branch | None:
        return db.get(Branch, branch_id)

    def list_active(self, db: Session) -> list[Branch]:
        return list(
            db.scalars(select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name))
        )

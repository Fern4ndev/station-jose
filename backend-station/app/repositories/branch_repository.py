"""Branch persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tables import Branch


class BranchRepository:
    def get_by_id(self, db: Session, branch_id: UUID) -> Branch | None:
        return db.get(Branch, branch_id)

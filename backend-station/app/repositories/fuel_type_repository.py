"""Fuel catalog persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tables import FuelType


class FuelTypeRepository:
    def list_active(self, db: Session) -> list[FuelType]:
        return list(db.scalars(select(FuelType).where(FuelType.is_active.is_(True)).order_by(FuelType.name)))

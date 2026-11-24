"""Fuel catalog persistence operations."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.tables import FuelType, PurchaseOrderItem


class FuelTypeRepository:
    def list_active(self, db: Session) -> list[FuelType]:
        return list(
            db.scalars(select(FuelType).where(FuelType.is_active.is_(True)).order_by(FuelType.name))
        )

    def list_all(
        self,
        db: Session,
        *,
        include_inactive: bool = True,
        q: str | None = None,
    ) -> list[FuelType]:
        statement = select(FuelType)
        if not include_inactive:
            statement = statement.where(FuelType.is_active.is_(True))
        term = (q or "").strip()
        if term:
            pattern = f"%{term}%"
            statement = statement.where(
                or_(FuelType.code.ilike(pattern), FuelType.name.ilike(pattern))
            )
        return list(db.scalars(statement.order_by(FuelType.name)))

    def get_by_id(self, db: Session, fuel_type_id: UUID) -> FuelType | None:
        return db.get(FuelType, fuel_type_id)

    def get_by_code(self, db: Session, code: str) -> FuelType | None:
        return db.scalar(select(FuelType).where(func.lower(FuelType.code) == code.lower()))

    def get_by_name(self, db: Session, name: str) -> FuelType | None:
        return db.scalar(select(FuelType).where(func.lower(FuelType.name) == name.lower()))

    def count_order_items(self, db: Session, fuel_type_id: UUID) -> int:
        return int(
            db.scalar(
                select(func.count(PurchaseOrderItem.id)).where(
                    PurchaseOrderItem.fuel_type_id == fuel_type_id
                )
            )
            or 0
        )

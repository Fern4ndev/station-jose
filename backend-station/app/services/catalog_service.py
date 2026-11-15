"""Read-only catalog use cases."""

from sqlalchemy.orm import Session

from app.repositories.branch_repository import BranchRepository
from app.repositories.fuel_type_repository import FuelTypeRepository
from app.tables import Branch, FuelType


class CatalogService:
    def __init__(self) -> None:
        self.branches = BranchRepository()
        self.fuel_types = FuelTypeRepository()

    def list_branches(self, db: Session) -> list[Branch]:
        return self.branches.list_active(db)

    def list_fuel_types(self, db: Session) -> list[FuelType]:
        return self.fuel_types.list_active(db)

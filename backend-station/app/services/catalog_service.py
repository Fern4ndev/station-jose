"""Catalog use cases."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ResourceNotFoundError
from app.repositories.branch_repository import BranchRepository
from app.repositories.fuel_type_repository import FuelTypeRepository
from app.schemas.catalog import FuelTypeCreate, FuelTypeUpdate
from app.tables import Branch, FuelType


class DuplicateFuelTypeError(AppError):
    status_code = 409
    code = "DUPLICATE_FUEL_TYPE"


class CatalogService:
    def __init__(self) -> None:
        self.branches = BranchRepository()
        self.fuel_types = FuelTypeRepository()

    def list_branches(self, db: Session) -> list[Branch]:
        return self.branches.list_active(db)

    def list_fuel_types(self, db: Session) -> list[FuelType]:
        return self.fuel_types.list_active(db)

    def list_fuel_types_manage(
        self,
        db: Session,
        *,
        q: str | None = None,
        include_inactive: bool = True,
    ) -> list[tuple[FuelType, int]]:
        fuels = self.fuel_types.list_all(db, include_inactive=include_inactive, q=q)
        return [(fuel, self.fuel_types.count_order_items(db, fuel.id)) for fuel in fuels]

    def create_fuel_type(self, db: Session, data: FuelTypeCreate) -> FuelType:
        self._ensure_unique(db, code=data.code, name=data.name)
        fuel = FuelType(code=data.code, name=data.name, is_active=data.is_active)
        db.add(fuel)
        db.flush()
        return fuel

    def update_fuel_type(
        self, db: Session, fuel_type_id: UUID, data: FuelTypeUpdate
    ) -> FuelType:
        fuel = self.get_fuel_type(db, fuel_type_id)
        self._ensure_unique(db, name=data.name, exclude_id=fuel.id)
        fuel.name = data.name
        db.flush()
        return fuel

    def set_fuel_type_status(
        self, db: Session, fuel_type_id: UUID, *, is_active: bool
    ) -> FuelType:
        fuel = self.get_fuel_type(db, fuel_type_id)
        fuel.is_active = is_active
        db.flush()
        return fuel

    def get_fuel_type(self, db: Session, fuel_type_id: UUID) -> FuelType:
        fuel = self.fuel_types.get_by_id(db, fuel_type_id)
        if fuel is None:
            raise ResourceNotFoundError("Combustible no encontrado.")
        return fuel

    def _ensure_unique(
        self,
        db: Session,
        *,
        name: str,
        code: str | None = None,
        exclude_id: UUID | None = None,
    ) -> None:
        if code is not None:
            existing_code = self.fuel_types.get_by_code(db, code)
            if existing_code is not None and existing_code.id != exclude_id:
                raise DuplicateFuelTypeError("Ya existe un combustible con ese código.")
        existing_name = self.fuel_types.get_by_name(db, name)
        if existing_name is not None and existing_name.id != exclude_id:
            raise DuplicateFuelTypeError("Ya existe un combustible con ese nombre.")

"""Fuel type administration endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.catalog import (
    FuelTypeCreate,
    FuelTypeManageResponse,
    FuelTypeResponse,
    FuelTypeStatusUpdate,
    FuelTypeUpdate,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/fuel-types", tags=["Fuel Types"])


@router.get(
    "/manage",
    response_model=list[FuelTypeManageResponse],
    dependencies=[Depends(require_permission("fuel_types.read"))],
)
def list_fuel_types_manage(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    include_inactive: bool = True,
) -> list[FuelTypeManageResponse]:
    return [
        FuelTypeManageResponse(
            **FuelTypeResponse.model_validate(fuel).model_dump(),
            created_at=fuel.created_at,
            orders_count=orders_count,
        )
        for fuel, orders_count in CatalogService().list_fuel_types_manage(
            db, q=q, include_inactive=include_inactive
        )
    ]


@router.post(
    "",
    response_model=FuelTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("fuel_types.manage"))],
)
def create_fuel_type(
    data: FuelTypeCreate, db: Annotated[Session, Depends(get_db)]
) -> FuelTypeResponse:
    fuel = CatalogService().create_fuel_type(db, data)
    db.commit()
    db.refresh(fuel)
    return FuelTypeResponse.model_validate(fuel)


@router.patch(
    "/{fuel_type_id}",
    response_model=FuelTypeResponse,
    dependencies=[Depends(require_permission("fuel_types.manage"))],
)
def update_fuel_type(
    fuel_type_id: UUID,
    data: FuelTypeUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> FuelTypeResponse:
    fuel = CatalogService().update_fuel_type(db, fuel_type_id, data)
    db.commit()
    db.refresh(fuel)
    return FuelTypeResponse.model_validate(fuel)


@router.patch(
    "/{fuel_type_id}/status",
    response_model=FuelTypeResponse,
    dependencies=[Depends(require_permission("fuel_types.manage"))],
)
def update_fuel_type_status(
    fuel_type_id: UUID,
    data: FuelTypeStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> FuelTypeResponse:
    fuel = CatalogService().set_fuel_type_status(db, fuel_type_id, is_active=data.is_active)
    db.commit()
    db.refresh(fuel)
    return FuelTypeResponse.model_validate(fuel)

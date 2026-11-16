"""Read-only catalog endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.database import get_db
from app.schemas.catalog import BranchResponse, FuelTypeResponse
from app.services.catalog_service import CatalogService

router = APIRouter(tags=["Branches", "Catalogs"])


@router.get("/branches", response_model=list[BranchResponse])
def list_branches(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[BranchResponse]:
    return [BranchResponse.model_validate(branch) for branch in CatalogService().list_branches(db)]


@router.get("/fuel-types", response_model=list[FuelTypeResponse])
def list_fuel_types(
    _: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[FuelTypeResponse]:
    return [FuelTypeResponse.model_validate(fuel) for fuel in CatalogService().list_fuel_types(db)]

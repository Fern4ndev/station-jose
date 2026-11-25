"""Purchase order request and response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalog import BranchResponse, FuelTypeResponse


class PurchaseOrderItemCreate(BaseModel):
    fuel_type_id: UUID
    authorized_gallons: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    total_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=60)
    siaf_number: str = Field(min_length=1, max_length=60)
    issue_date: date
    institution_name: str = Field(min_length=1, max_length=200)
    institution_ruc: str = Field(pattern=r"^\d{11}$")
    supplier_name: str = Field(min_length=1, max_length=200)
    supplier_details: str | None = None
    branch_id: UUID
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distinct_fuels(self) -> "PurchaseOrderCreate":
        fuel_ids = [item.fuel_type_id for item in self.items]
        if len(fuel_ids) != len(set(fuel_ids)):
            raise ValueError("Cada combustible solo puede aparecer una vez por orden.")
        return self


class PurchaseOrderUpdate(BaseModel):
    siaf_number: str | None = Field(default=None, min_length=1, max_length=60)
    issue_date: date | None = None
    institution_name: str | None = Field(default=None, min_length=1, max_length=200)
    institution_ruc: str | None = Field(default=None, pattern=r"^\d{11}$")
    supplier_name: str | None = Field(default=None, min_length=1, max_length=200)
    supplier_details: str | None = None
    branch_id: UUID | None = None
    items: list[PurchaseOrderItemCreate] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_distinct_fuels(self) -> "PurchaseOrderUpdate":
        if self.items is not None:
            fuel_ids = [item.fuel_type_id for item in self.items]
            if len(fuel_ids) != len(set(fuel_ids)):
                raise ValueError("Cada combustible solo puede aparecer una vez por orden.")
        return self


class PurchaseOrderItemResponse(BaseModel):
    id: UUID
    fuel_type: FuelTypeResponse
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str
    unit_price: Decimal
    total_amount: Decimal


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    siaf_number: str
    issue_date: date
    institution_name: str
    supplier_name: str
    supplier_details: str | None
    executing_unit: str
    executing_unit_ruc: str
    branch: BranchResponse
    deleted_at: datetime | None
    items: list[PurchaseOrderItemResponse]
    status: str


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderResponse]
    pagination: PaginationResponse

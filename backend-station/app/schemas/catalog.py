"""Catalog response and management schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FUEL_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")


class FuelTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_active: bool


class FuelTypeManageResponse(FuelTypeResponse):
    created_at: datetime
    orders_count: int


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_active: bool


def _normalize_code(value: str) -> str:
    normalized = "-".join(value.strip().upper().split())
    if not FUEL_CODE_PATTERN.fullmatch(normalized):
        raise ValueError("El código solo admite letras, números, guiones y guiones bajos.")
    return normalized


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("El nombre del combustible es obligatorio.")
    return normalized


class FuelTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_name(value)


class FuelTypeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_name(value)


class FuelTypeStatusUpdate(BaseModel):
    is_active: bool

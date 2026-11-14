"""Common API response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class UserListResponse(BaseModel):
    items: list[Any]
    pagination: Pagination

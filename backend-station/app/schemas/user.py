"""User management schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.permissions import UserRole
from app.schemas.auth import BranchSummary


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=150)
    dni: str = Field(min_length=1, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    branch_id: UUID | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> "UserCreate":
        if self.role == UserRole.ATTENDANT and self.branch_id is None:
            raise ValueError("branch_id is required for ATTENDANT users")
        return self


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=150)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: UserRole
    branch_id: UUID | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> "UserRoleUpdate":
        if self.role == UserRole.ATTENDANT and self.branch_id is None:
            raise ValueError("branch_id is required for ATTENDANT users")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    dni: str
    email: EmailStr
    role: UserRole
    branch: BranchSummary | None = None
    is_active: bool

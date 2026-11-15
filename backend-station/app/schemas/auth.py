"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    permissions: list[str]


class CurrentUserResponse(UserResponse):
    permissions: list[str]

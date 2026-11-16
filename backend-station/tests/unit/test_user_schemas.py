"""User request schema validation tests."""

from uuid import uuid4

import pytest
from app.schemas.user import UserCreate, UserRoleUpdate
from pydantic import ValidationError


def test_office_user_can_be_created_without_branch() -> None:
    user = UserCreate(
        first_name="Office",
        last_name="User",
        dni="12345678",
        email="office@example.com",
        password="secure-password",
        role="OFFICE",
    )

    assert user.branch_id is None


def test_office_user_cannot_be_assigned_to_a_branch() -> None:
    with pytest.raises(ValidationError, match="branch_id must be omitted"):
        UserCreate(
            first_name="Office",
            last_name="User",
            dni="12345678",
            email="office@example.com",
            password="secure-password",
            role="OFFICE",
            branch_id=uuid4(),
        )


def test_office_role_update_cannot_be_assigned_to_a_branch() -> None:
    with pytest.raises(ValidationError, match="branch_id must be omitted"):
        UserRoleUpdate(role="OFFICE", branch_id=uuid4())

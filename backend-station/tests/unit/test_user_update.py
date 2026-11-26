from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.schemas.user import UserUpdate
from app.services.user_service import DuplicateUserError, UserService


def _service(user: SimpleNamespace) -> UserService:
    service = UserService()
    service.users = Mock()
    service.users.get_by_id.return_value = user
    service.sessions = Mock()
    return service


def test_update_user_rejects_dni_of_another_user() -> None:
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id, role="OFFICE", first_name="Ana", last_name="Pérez", dni="11111111",
        email="ana@example.com",
    )
    service = _service(user)
    service.users.get_by_dni.return_value = SimpleNamespace(id=uuid4())

    with pytest.raises(DuplicateUserError):
        service.update_user(Mock(), user_id, UserUpdate(dni="22222222"))

    assert user.dni == "11111111"


def test_update_user_rejects_email_of_another_user() -> None:
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id, role="OFFICE", first_name="Ana", last_name="Pérez", dni="11111111",
        email="ana@example.com",
    )
    service = _service(user)
    service.users.get_by_email.return_value = SimpleNamespace(id=uuid4())

    with pytest.raises(DuplicateUserError):
        service.update_user(Mock(), user_id, UserUpdate(email="otra@example.com"))

    assert user.email == "ana@example.com"


def test_update_user_allows_keeping_own_dni_and_email() -> None:
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id, role="OFFICE", first_name="Ana", last_name="Pérez", dni="11111111",
        email="ana@example.com",
    )
    service = _service(user)
    service.users.get_by_dni.return_value = user
    service.users.get_by_email.return_value = user

    service.update_user(Mock(), user_id, UserUpdate(dni="11111111", email="ANA@example.com"))

    assert user.dni == "11111111"
    assert user.email == "ana@example.com"
    service.sessions.revoke_all_for_user.assert_not_called()


def test_update_user_revokes_sessions_when_email_changes() -> None:
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id, role="OFFICE", first_name="Ana", last_name="Pérez", dni="11111111",
        email="ana@example.com",
    )
    service = _service(user)
    service.users.get_by_email.return_value = None

    service.update_user(Mock(), user_id, UserUpdate(email="NUEVA@example.com"))

    assert user.email == "nueva@example.com"
    service.sessions.revoke_all_for_user.assert_called_once()

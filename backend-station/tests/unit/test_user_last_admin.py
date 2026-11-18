from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.schemas.user import UserRoleUpdate, UserStatusUpdate
from app.services.user_service import LastActiveAdminError, UserService


@pytest.mark.parametrize("operation", ["status", "role"])
def test_last_active_admin_cannot_be_disabled_or_demoted(operation: str) -> None:
    user_id = uuid4()
    service = UserService()
    service.users = Mock()
    service.users.get_by_id.return_value = SimpleNamespace(id=user_id, role="ADMIN", is_active=True)
    service.users.count_active_admins.return_value = 1
    with pytest.raises(LastActiveAdminError):
        if operation == "status":
            service.set_status(Mock(), user_id, UserStatusUpdate(is_active=False))
        else:
            service.set_role(Mock(), user_id, UserRoleUpdate(role="OFFICE"))

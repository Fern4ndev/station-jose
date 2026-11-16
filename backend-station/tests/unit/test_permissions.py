"""RBAC policy tests."""

from app.core.permissions import UserRole, permissions_for_role


def test_admin_has_user_management_permission() -> None:
    assert "users.manage" in permissions_for_role(UserRole.ADMIN)


def test_attendant_cannot_manage_users_or_reports() -> None:
    permissions = permissions_for_role(UserRole.ATTENDANT)

    assert "users.manage" not in permissions
    assert "reports.read" not in permissions
    assert "attendances.create" in permissions

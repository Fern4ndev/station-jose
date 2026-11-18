"""Authentication contract tests that do not require a live database."""

from types import SimpleNamespace
from uuid import uuid4

from app.routers.auth import me
from fastapi.testclient import TestClient


def test_auth_routes_are_exposed(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/auth/login" in openapi["paths"]
    assert "/api/v1/auth/logout" in openapi["paths"]
    assert "/api/v1/auth/me" in openapi["paths"]
    assert "/api/v1/users" in openapi["paths"]


def test_me_includes_effective_permissions() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        first_name="Ana",
        last_name="Prueba",
        dni="12345678",
        email="ana@example.com",
        role="ADMIN",
        branch=None,
        is_active=True,
    )
    response = me(user)
    assert response.role == "ADMIN"
    assert "users.manage" in response.permissions

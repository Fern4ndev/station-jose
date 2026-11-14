"""Authentication contract tests that do not require a live database."""

from fastapi.testclient import TestClient


def test_auth_routes_are_exposed(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()

    assert "/api/v1/auth/login" in openapi["paths"]
    assert "/api/v1/auth/logout" in openapi["paths"]
    assert "/api/v1/auth/me" in openapi["paths"]
    assert "/api/v1/users" in openapi["paths"]

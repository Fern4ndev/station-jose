"""Fuel type administration routes are part of the public contract."""

from app.core.permissions import permissions_for_role
from fastapi.testclient import TestClient


def test_fuel_type_management_routes_are_exposed(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    for path in (
        "/api/v1/fuel-types",
        "/api/v1/fuel-types/manage",
        "/api/v1/fuel-types/{fuel_type_id}",
        "/api/v1/fuel-types/{fuel_type_id}/status",
    ):
        assert path in paths


def test_only_admin_can_manage_fuel_types() -> None:
    assert "fuel_types.manage" in permissions_for_role("ADMIN")
    assert "fuel_types.read" in permissions_for_role("ADMIN")

    for role in ("OFFICE", "ATTENDANT"):
        assert "fuel_types.manage" not in permissions_for_role(role)
        assert "fuel_types.read" not in permissions_for_role(role)

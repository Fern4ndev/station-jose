"""Read endpoints required by the backend plan are exposed with role boundaries."""

from app.core.permissions import permissions_for_role
from fastapi.testclient import TestClient


def test_operational_read_routes_match_plan(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v1/attendances",
        "/api/v1/attendances/{attendance_id}",
        "/api/v1/users/{user_id}/attendances",
        "/api/v1/balances/purchase-orders/{order_id}",
        "/api/v1/balances/vouchers/{voucher_id}",
        "/api/v1/balances/overview",
        "/api/v1/dashboard",
    ):
        assert path in paths


def test_admin_can_supervise_attendances() -> None:
    assert "attendances.read_all" in permissions_for_role("ADMIN")
    assert "attendances.create" in permissions_for_role("ADMIN")
    assert "attendances.read_all" not in permissions_for_role("ATTENDANT")

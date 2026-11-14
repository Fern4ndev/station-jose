"""API tests for health checks."""

from fastapi.testclient import TestClient


def test_live_check_does_not_require_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_check_reports_database_failure_without_leaking_internals(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code in {200, 503}
    if response.status_code == 503:
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert "postgresql" not in str(body).lower()

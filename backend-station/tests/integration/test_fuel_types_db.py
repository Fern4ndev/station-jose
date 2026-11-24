"""Fuel type administration integration against a disposable transaction."""

import os
from collections.abc import Generator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.core.dependencies import get_current_user
from app.database import engine, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skipif(
    os.getenv("SANJOSE_RUN_DB_TESTS") != "1", reason="Database integration requires explicit opt-in"
)


@pytest.fixture
def client_db() -> Generator[TestClient, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    def override_db() -> Generator[Session, None, None]:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="ADMIN")
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        transaction.rollback()
        connection.close()


def test_fuel_type_lifecycle(client_db: TestClient) -> None:
    suffix = uuid4().hex[:8].upper()
    payload = {"code": f"test-fuel-{suffix}", "name": f"Combustible {suffix}"}

    created = client_db.post("/api/v1/fuel-types", json=payload)
    assert created.status_code == 201
    fuel_id = created.json()["id"]
    assert created.json()["code"] == f"TEST-FUEL-{suffix}"
    assert created.json()["is_active"] is True

    duplicate = client_db.post("/api/v1/fuel-types", json={**payload, "name": "Otro nombre"})
    assert duplicate.status_code == 409

    renamed = client_db.patch(
        f"/api/v1/fuel-types/{fuel_id}", json={"name": f"Combustible editado {suffix}"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == f"Combustible editado {suffix}"

    disabled = client_db.patch(f"/api/v1/fuel-types/{fuel_id}/status", json={"is_active": False})
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False

    listed = client_db.get("/api/v1/fuel-types/manage", params={"q": suffix})
    assert listed.status_code == 200
    row = next(item for item in listed.json() if item["id"] == fuel_id)
    assert row["is_active"] is False
    assert row["orders_count"] == 0

    active_catalog = client_db.get("/api/v1/fuel-types")
    assert fuel_id not in {item["id"] for item in active_catalog.json()}


def test_office_cannot_manage_fuel_types(client_db: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="OFFICE")

    assert client_db.get("/api/v1/fuel-types/manage").status_code == 403
    assert (
        client_db.post(
            "/api/v1/fuel-types", json={"code": "DIESEL-X", "name": "Diésel X"}
        ).status_code
        == 403
    )

"""User API integration against an explicitly selected disposable transaction."""

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


def test_user_lifecycle_and_duplicate(client_db: TestClient) -> None:
    suffix = uuid4().hex[:12]
    request = {
        "first_name": "Prueba",
        "last_name": "Temporal",
        "dni": suffix,
        "email": f"test-{suffix}@example.com",
        "password": "temporary123",
        "role": "OFFICE",
        "branch_id": None,
    }
    created = client_db.post("/api/v1/users", json=request)
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert client_db.post("/api/v1/users", json=request).status_code == 409
    assert client_db.get(f"/api/v1/users/{user_id}").json()["first_name"] == "Prueba"
    changed = client_db.patch(f"/api/v1/users/{user_id}", json={"first_name": "Editado"})
    assert changed.status_code == 200 and changed.json()["first_name"] == "Editado"
    role = client_db.patch(
        f"/api/v1/users/{user_id}/role", json={"role": "ADMIN", "branch_id": None}
    )
    assert role.status_code == 200 and role.json()["role"] == "ADMIN"
    disabled = client_db.patch(f"/api/v1/users/{user_id}/status", json={"is_active": False})
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False
    enabled = client_db.patch(f"/api/v1/users/{user_id}/status", json={"is_active": True})
    assert enabled.status_code == 200 and enabled.json()["is_active"] is True


def test_office_cannot_list_users(client_db: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="OFFICE")
    assert client_db.get("/api/v1/users").status_code == 403

"""Purchase-order API tests, executed only when explicitly enabled."""

import os
from collections.abc import Generator
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.core.dependencies import get_current_user
from app.database import engine, get_db
from app.main import app
from app.tables import Branch, FuelType, User, Voucher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skipif(
    os.getenv("SANJOSE_RUN_DB_TESTS") != "1", reason="Database integration requires explicit opt-in"
)

INSTITUTION_FIELDS = {
    "institution_name": "Institución de prueba",
    "institution_ruc": "20123456789",
}


@pytest.fixture
def order_context() -> Generator[tuple[TestClient, str, list[str], Session], None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    setup = Session(bind=connection, join_transaction_mode="create_savepoint")
    suffix = uuid4().hex[:8]
    branch = Branch(id=uuid4(), code=f"T{suffix}", name=f"Test {suffix}")
    fuels = [FuelType(id=uuid4(), code=f"T{suffix}{i}", name=f"Fuel {suffix} {i}") for i in (1, 2)]
    setup.add_all([branch, *fuels])
    setup.flush()
    branch_id = str(branch.id)
    fuel_ids = [str(item.id) for item in fuels]
    setup.commit()

    def override_db() -> Generator[Session, None, None]:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="ADMIN")
    try:
        with TestClient(app) as client:
            yield client, branch_id, fuel_ids, setup
    finally:
        app.dependency_overrides.clear()
        setup.close()
        transaction.rollback()
        connection.close()


def test_order_lifecycle_and_filters(
    order_context: tuple[TestClient, str, list[str], Session],
) -> None:
    client, branch_id, fuels, _ = order_context
    number = f"F3-{uuid4().hex[:10]}"
    body = {
        "order_number": number,
        "siaf_number": "SIAF-TEST",
        "issue_date": "2026-11-01",
        **INSTITUTION_FIELDS,
        "supplier_name": "Proveedor",
        "branch_id": branch_id,
        "items": [
            {
                "fuel_type_id": fuel,
                "authorized_gallons": "10.000",
                "unit_price": "10.0000",
                "total_amount": "100.00",
            }
            for fuel in fuels
        ],
    }
    duplicate = {**body, "items": [body["items"][0], body["items"][0]]}
    assert client.post("/api/v1/purchase-orders", json=duplicate).status_code == 422
    created = client.post("/api/v1/purchase-orders", json=body)
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert len(created.json()["items"]) == 2
    found = client.get(
        "/api/v1/purchase-orders",
        params={
            "search": number,
            "branch_id": branch_id,
            "issue_date_from": "2026-11-01",
        },
    )
    assert found.status_code == 200 and found.json()["items"][0]["id"] == order_id
    found_by_ruc = client.get(
        "/api/v1/purchase-orders",
        params={"search": INSTITUTION_FIELDS["institution_ruc"]},
    )
    assert found_by_ruc.status_code == 200
    assert any(item["id"] == order_id for item in found_by_ruc.json()["items"])
    updated = client.patch(
        f"/api/v1/purchase-orders/{order_id}", json={"supplier_name": "Proveedor actualizado"}
    )
    assert (
        updated.status_code == 200 and updated.json()["supplier_name"] == "Proveedor actualizado"
    )
    assert client.delete(f"/api/v1/purchase-orders/{order_id}").status_code == 204
    assert client.get(f"/api/v1/purchase-orders/{order_id}").status_code == 404


def test_order_with_voucher_cannot_be_deleted(
    order_context: tuple[TestClient, str, list[str], Session],
) -> None:
    client, branch_id, fuels, session = order_context
    body = {
        "order_number": f"F3-{uuid4().hex[:10]}",
        "siaf_number": "SIAF",
        "issue_date": "2026-11-01",
        **INSTITUTION_FIELDS,
        "supplier_name": "Proveedor",
        "branch_id": branch_id,
        "items": [
            {
                "fuel_type_id": fuels[0],
                "authorized_gallons": "10",
                "unit_price": "1",
                "total_amount": "10",
            }
        ],
    }
    created = client.post("/api/v1/purchase-orders", json=body)
    assert created.status_code == 201
    order_id = created.json()["id"]
    session.add(
        Voucher(
            id=uuid4(),
            purchase_order_id=order_id,
            issuer_type="INSTITUTION",
            issuer_name="Entidad",
            issuer_normalized="entidad",
            voucher_number="TEST",
            voucher_number_normalized="test",
        )
    )
    session.flush()
    response = client.delete(f"/api/v1/purchase-orders/{order_id}")
    assert response.status_code == 409


def test_partial_dispatch_preserves_voucher_balance_and_idempotency(
    order_context: tuple[TestClient, str, list[str], Session],
) -> None:
    client, branch_id, fuels, session = order_context
    actor_id = uuid4()
    suffix = uuid4().hex[:12]
    dispatch_branch_id = uuid4()
    session.add(Branch(id=dispatch_branch_id, code=f"D{suffix[:8]}", name=f"Despacho {suffix}"))
    session.add(
        User(
            id=actor_id,
            first_name="Test",
            last_name="F4",
            dni=suffix,
            email=f"f4-{suffix}@example.com",
            password_hash="disabled",
            role="ATTENDANT",
            branch_id=dispatch_branch_id,
        )
    )
    session.flush()
    body = {
        "order_number": f"F4-{suffix}",
        "siaf_number": "SIAF",
        "issue_date": "2026-11-01",
        **INSTITUTION_FIELDS,
        "supplier_name": "Proveedor",
        "branch_id": branch_id,
        "items": [
            {
                "fuel_type_id": fuel,
                "authorized_gallons": "20",
                "unit_price": "1",
                "total_amount": "20",
            }
            for fuel in fuels
        ],
    }
    order = client.post("/api/v1/purchase-orders", json=body)
    assert order.status_code == 201
    order_id = order.json()["id"]
    line1, line2 = [item["id"] for item in order.json()["items"]]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role="ATTENDANT", id=actor_id, branch_id=dispatch_branch_id
    )
    payload = {
        "issuer_type": "INSTITUTION",
        "issuer_name": "Entidad",
        "voucher_number": f"V-{suffix}",
        "voucher_items": [
            {"purchase_order_item_id": line1, "authorized_gallons": "10"},
            {"purchase_order_item_id": line2, "authorized_gallons": "4"},
        ],
        "items": [{"purchase_order_item_id": line1, "attended_gallons": "5"}],
    }
    key = str(uuid4())
    first = client.post(
        f"/api/v1/purchase-orders/{order_id}/attendances",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 201, first.text
    assert first.json()["branch_id"] == str(dispatch_branch_id)
    assert "unit_price_snapshot" not in first.json()["items"][0]
    replay = client.post(
        f"/api/v1/purchase-orders/{order_id}/attendances",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert replay.status_code == 201 and replay.json()["id"] == first.json()["id"]
    voucher_id = first.json()["voucher_id"]
    voucher = client.get(f"/api/v1/vouchers/{voucher_id}").json()
    by_order = {line["purchase_order_item_id"]: line for line in voucher["items"]}
    assert float(by_order[line1]["available_gallons"]) == 5
    assert float(by_order[line2]["available_gallons"]) == 4
    order_balance = client.get(f"/api/v1/balances/purchase-orders/{order_id}")
    assert order_balance.status_code == 200
    assert float(order_balance.json()["items"][0]["available_gallons"]) == 15
    voucher_balance = client.get(f"/api/v1/balances/vouchers/{voucher_id}")
    assert voucher_balance.status_code == 200
    assert float(voucher_balance.json()["items"][0]["available_gallons"]) == 5
    overview = client.get("/api/v1/balances/overview")
    assert overview.status_code == 200
    assert overview.json()["pagination"]["total"] >= 1
    attendances = client.get("/api/v1/attendances")
    assert attendances.status_code == 200
    assert attendances.json()["pagination"]["total"] == 1
    assert "unit_price_snapshot" not in attendances.json()["items"][0]["items"][0]
    assert client.get(f"/api/v1/attendances/{first.json()['id']}").status_code == 200
    assert client.get(f"/api/v1/users/{actor_id}/attendances").status_code == 403
    follow_up = client.post(
        f"/api/v1/vouchers/{voucher_id}/attendances",
        headers={"Idempotency-Key": str(uuid4())},
        json={"items": [{"voucher_item_id": by_order[line1]["id"], "attended_gallons": "5"}]},
    )
    assert follow_up.status_code == 201, follow_up.text
    excess = client.post(
        f"/api/v1/vouchers/{voucher_id}/attendances",
        headers={"Idempotency-Key": str(uuid4())},
        json={"items": [{"voucher_item_id": by_order[line1]["id"], "attended_gallons": "1"}]},
    )
    assert excess.status_code == 409


def test_review_and_correction_preserve_balances(
    order_context: tuple[TestClient, str, list[str], Session],
) -> None:
    client, branch_id, fuels, session = order_context
    suffix = uuid4().hex[:12]
    attendant_id, reviewer_id = uuid4(), uuid4()
    session.add_all(
        [
            User(
                id=attendant_id,
                first_name="Test",
                last_name="Attendant",
                dni=f"a{suffix}",
                email=f"a{suffix}@example.com",
                password_hash="disabled",
                role="ATTENDANT",
                branch_id=branch_id,
            ),
            User(
                id=reviewer_id,
                first_name="Test",
                last_name="Office",
                dni=f"o{suffix}",
                email=f"o{suffix}@example.com",
                password_hash="disabled",
                role="OFFICE",
            ),
        ]
    )
    session.flush()
    order_body = {
        "order_number": f"F5-{suffix}",
        "siaf_number": "SIAF",
        "issue_date": "2026-11-01",
        **INSTITUTION_FIELDS,
        "supplier_name": "Proveedor",
        "branch_id": branch_id,
        "items": [
            {
                "fuel_type_id": fuels[0],
                "authorized_gallons": "20",
                "unit_price": "1",
                "total_amount": "20",
            }
        ],
    }
    order = client.post("/api/v1/purchase-orders", json=order_body)
    assert order.status_code == 201
    order_id, line_id = order.json()["id"], order.json()["items"][0]["id"]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role="ATTENDANT", id=attendant_id, branch_id=UUID(branch_id)
    )
    first = client.post(
        f"/api/v1/purchase-orders/{order_id}/attendances",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "issuer_type": "INSTITUTION",
            "issuer_name": "Entidad",
            "voucher_number": f"V-{suffix}",
            "voucher_items": [{"purchase_order_item_id": line_id, "authorized_gallons": "10"}],
            "items": [{"purchase_order_item_id": line_id, "attended_gallons": "5"}],
        },
    )
    assert first.status_code == 201, first.text
    voucher_id = first.json()["voucher_id"]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role="OFFICE", id=reviewer_id, branch_id=None
    )
    before = client.get(f"/api/v1/purchase-orders/{order_id}").json()["items"][0][
        "available_gallons"
    ]
    user_attendances = client.get(f"/api/v1/users/{attendant_id}/attendances")
    assert user_attendances.json()["pagination"]["total"] == 1
    assert (
        client.patch(
            f"/api/v1/vouchers/{voucher_id}/descriptive-data", json={"issuer_name": "Otro"}
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/vouchers/{voucher_id}").status_code == 409
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role="ADMIN", id=reviewer_id, branch_id=None
    )
    corrected = client.patch(
        f"/api/v1/vouchers/{voucher_id}/descriptive-data", json={"issuer_name": "Entidad corregida"}
    )
    assert corrected.status_code == 200
    assert corrected.json()["issuer_name"] == "Entidad corregida"
    assert (
        client.get(f"/api/v1/purchase-orders/{order_id}").json()["items"][0]["available_gallons"]
        == before
    )


def test_reports_filter_export_and_role_access(
    order_context: tuple[TestClient, str, list[str], Session],
) -> None:
    client, branch_id, fuels, _ = order_context
    body = {
        "order_number": f"F6-{uuid4().hex[:10]}",
        "siaf_number": "SIAF",
        "issue_date": "2026-11-01",
        **INSTITUTION_FIELDS,
        "supplier_name": "Proveedor",
        "branch_id": branch_id,
        "items": [
            {
                "fuel_type_id": fuels[0],
                "authorized_gallons": "10",
                "unit_price": "1",
                "total_amount": "10",
            }
        ],
    }
    assert client.post("/api/v1/purchase-orders", json=body).status_code == 201
    filters = {"date_from": "2026-11-01", "date_to": "2026-11-01", "branch_id": branch_id}
    report = client.get("/api/v1/reports/purchase-orders", params=filters)
    assert report.status_code == 200 and report.json()["total"] == 1
    assert (
        client.get("/api/v1/reports/dashboard", params={**filters, "group_by": "month"}).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/reports/attendances",
            params={"date_from": "2026-12-01", "date_to": "2026-01-01"},
        ).status_code
        == 422
    )
    for kind in ("purchase-orders", "attendances"):
        for extension, signature in (("pdf", b"%PDF"), ("xlsx", b"PK")):
            response = client.get(
                f"/api/v1/reports/{kind}/export", params={**filters, "format": extension}
            )
            assert response.status_code == 200
            assert response.content.startswith(signature)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="ATTENDANT")
    assert client.get("/api/v1/reports/dashboard").status_code == 403
    assert (
        client.get("/api/v1/reports/purchase-orders/export", params={"format": "pdf"}).status_code
        == 403
    )

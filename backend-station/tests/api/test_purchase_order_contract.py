"""Purchase order and catalog OpenAPI contract tests."""

from fastapi.testclient import TestClient


def test_purchase_order_routes_are_exposed(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/api/v1/branches" in paths
    assert "/api/v1/fuel-types" in paths
    assert "/api/v1/purchase-orders" in paths
    assert "/api/v1/purchase-orders/{order_id}" in paths


def test_purchase_order_create_contract_has_items(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["PurchaseOrderCreate"]

    assert "items" in schema["required"]
    assert "institution_name" in schema["required"]
    assert "institution_ruc" in schema["required"]
    assert schema["properties"]["items"]["minItems"] == 1

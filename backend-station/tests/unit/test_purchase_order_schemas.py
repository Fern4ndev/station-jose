"""Purchase order schema validation tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from app.schemas.purchase_order import PurchaseOrderCreate
from pydantic import ValidationError


def test_purchase_order_requires_at_least_one_line() -> None:
    with pytest.raises(ValidationError):
        PurchaseOrderCreate(
            order_number="OC-001",
            siaf_number="SIAF-001",
            issue_date="2026-01-01",
            institution_name="Institución",
            institution_ruc="20123456789",
            supplier_name="Proveedor",
            branch_id=uuid4(),
            items=[],
        )


def test_purchase_order_rejects_repeated_fuel_lines() -> None:
    fuel_id = uuid4()

    with pytest.raises(ValidationError):
        PurchaseOrderCreate(
            order_number="OC-001",
            siaf_number="SIAF-001",
            issue_date="2026-01-01",
            institution_name="Institución",
            institution_ruc="20123456789",
            supplier_name="Proveedor",
            branch_id=uuid4(),
            items=[
                {
                    "fuel_type_id": fuel_id,
                    "authorized_gallons": Decimal("10.000"),
                    "unit_price": Decimal("15.2500"),
                    "total_amount": Decimal("152.50"),
                },
                {
                    "fuel_type_id": fuel_id,
                    "authorized_gallons": Decimal("5.000"),
                    "unit_price": Decimal("15.2500"),
                    "total_amount": Decimal("76.25"),
                },
            ],
        )


def test_purchase_order_rejects_invalid_institution_ruc() -> None:
    with pytest.raises(ValidationError):
        PurchaseOrderCreate(
            order_number="OC-001",
            siaf_number="SIAF-001",
            issue_date="2026-01-01",
            institution_name="Institución",
            institution_ruc="123",
            supplier_name="Proveedor",
            branch_id=uuid4(),
            items=[
                {
                    "fuel_type_id": uuid4(),
                    "authorized_gallons": "10",
                    "unit_price": "1",
                    "total_amount": "10",
                }
            ],
        )

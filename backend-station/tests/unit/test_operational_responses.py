from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.operational import OperationalAttendance, OperationalOrderItem


def test_attendance_excludes_financial_values() -> None:
    item_id = uuid4()
    payload = {
        "id": uuid4(), "voucher_id": uuid4(), "performed_by_user_id": uuid4(), "branch_id": uuid4(),
        "attended_at": datetime.now(UTC), "idempotency_key": uuid4(), "verifications": [],
        "items": [{"id": item_id, "voucher_item_id": uuid4(), "attended_gallons": "5.000", "unit_price_snapshot": "10.0000", "attended_amount": "50.00"}],
    }
    item = OperationalAttendance.model_validate(payload).model_dump(mode="json")["items"][0]
    assert "unit_price_snapshot" not in item
    assert "attended_amount" not in item
    assert item["attended_gallons"] == "5.000"


def test_order_line_excludes_financial_values() -> None:
    line = OperationalOrderItem.model_validate({
        "id": uuid4(), "fuel_type": {"id": uuid4(), "code": "D", "name": "Diesel", "is_active": True},
        "authorized_gallons": "10", "attended_gallons": "2", "available_gallons": "8", "status": "PENDING",
        "unit_price": "10", "total_amount": "100",
    }).model_dump(mode="json")
    assert "unit_price" not in line
    assert "total_amount" not in line

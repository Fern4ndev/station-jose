from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.operational import OperationalAttendance, OperationalOrderItem, operational_voucher


def test_attendance_excludes_financial_values() -> None:
    item_id = uuid4()
    payload = {
        "id": uuid4(),
        "voucher_id": uuid4(),
        "performed_by_user_id": uuid4(),
        "branch_id": uuid4(),
        "attended_at": datetime.now(UTC),
        "idempotency_key": uuid4(),
        "items": [
            {
                "id": item_id,
                "voucher_item_id": uuid4(),
                "attended_gallons": "5.000",
                "unit_price_snapshot": "10.0000",
                "attended_amount": "50.00",
            }
        ],
    }
    item = OperationalAttendance.model_validate(payload).model_dump(mode="json")["items"][0]
    assert "unit_price_snapshot" not in item
    assert "attended_amount" not in item
    assert item["attended_gallons"] == "5.000"


def test_order_line_excludes_financial_values() -> None:
    line = OperationalOrderItem.model_validate(
        {
            "id": uuid4(),
            "fuel_type": {"id": uuid4(), "code": "D", "name": "Diesel", "is_active": True},
            "authorized_gallons": "10",
            "attended_gallons": "2",
            "available_gallons": "8",
            "status": "PENDING",
            "unit_price": "10",
            "total_amount": "100",
        }
    ).model_dump(mode="json")
    assert "unit_price" not in line
    assert "total_amount" not in line


def test_operational_voucher_exposes_only_the_attendants_own_history() -> None:
    user_id, other_id, voucher_id = uuid4(), uuid4(), uuid4()

    def attendance(actor: object) -> dict:
        return {
            "id": uuid4(),
            "voucher_id": voucher_id,
            "performed_by_user_id": actor,
            "branch_id": uuid4(),
            "attended_at": datetime.now(UTC),
            "idempotency_key": uuid4(),
            "items": [],
        }

    payload = {
        "id": voucher_id,
        "purchase_order_id": uuid4(),
        "issuer_type": "INSTITUTION",
        "issuer_name": "Entidad",
        "voucher_number": "V1",
        "created_at": datetime.now(UTC),
        "status": "PENDING",
        "items": [],
        "attendances": [attendance(user_id), attendance(other_id)],
    }
    result = operational_voucher(payload, user_id)
    assert len(result.attendances) == 1
    assert result.attendances[0].performed_by_user_id == user_id

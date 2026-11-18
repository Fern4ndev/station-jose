from uuid import uuid4

import pytest
from app.schemas.attendance import FirstAttendanceCreate, FollowUpAttendanceCreate
from pydantic import ValidationError


def test_first_attendance_accepts_authorized_lines_without_dispatch() -> None:
    first, second = uuid4(), uuid4()
    request = FirstAttendanceCreate(
        issuer_type="INSTITUTION",
        issuer_name="Entidad",
        voucher_number="V-1",
        voucher_items=[
            {"purchase_order_item_id": first, "authorized_gallons": "10"},
            {"purchase_order_item_id": second, "authorized_gallons": "4"},
        ],
        items=[{"purchase_order_item_id": first, "attended_gallons": "5"}],
    )
    assert len(request.voucher_items) == 2
    assert len(request.items) == 1


def test_first_attendance_rejects_dispatch_exceeding_voucher_authorization() -> None:
    item = uuid4()
    with pytest.raises(ValidationError):
        FirstAttendanceCreate(
            issuer_type="INSTITUTION",
            issuer_name="Entidad",
            voucher_number="V-1",
            voucher_items=[{"purchase_order_item_id": item, "authorized_gallons": "4"}],
            items=[{"purchase_order_item_id": item, "attended_gallons": "5"}],
        )


def test_follow_up_requires_a_voucher_line() -> None:
    with pytest.raises(ValidationError):
        FollowUpAttendanceCreate(
            items=[{"purchase_order_item_id": uuid4(), "attended_gallons": "1"}]
        )

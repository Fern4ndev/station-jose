from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import IdempotencyConflictError
from app.schemas.attendance import AttendanceCreate
from app.services.attendance_service import AttendanceService, fingerprint


def test_replay_rejects_another_user() -> None:
    data = AttendanceCreate(items=[{"voucher_item_id": str(uuid4()), "attended_gallons": "1.000"}])
    existing = SimpleNamespace(id=uuid4(), request_fingerprint=fingerprint(data), performed_by_user_id=uuid4(), voucher_id=uuid4())
    service = AttendanceService()
    service.vouchers = Mock()
    service.vouchers.get_attendance_by_idempotency.return_value = existing
    with pytest.raises(IdempotencyConflictError):
        service._resolve_idempotency(Mock(), uuid4(), data, user_id=uuid4(), voucher_id=existing.voucher_id)


def test_replay_requires_same_voucher_and_allows_identical_retry() -> None:
    data = AttendanceCreate(items=[{"voucher_item_id": str(uuid4()), "attended_gallons": "1.000"}])
    user_id, voucher_id = uuid4(), uuid4()
    existing = SimpleNamespace(id=uuid4(), request_fingerprint=fingerprint(data), performed_by_user_id=user_id, voucher_id=voucher_id)
    service = AttendanceService()
    service.vouchers = Mock()
    service.vouchers.get_attendance_by_idempotency.return_value = existing
    assert service._resolve_idempotency(Mock(), uuid4(), data, user_id=user_id, voucher_id=voucher_id) is existing
    with pytest.raises(IdempotencyConflictError):
        service._resolve_idempotency(Mock(), uuid4(), data, user_id=user_id, voucher_id=uuid4())

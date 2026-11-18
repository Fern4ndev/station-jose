from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services.verification_service import VerificationService


def test_pending_list_distinguishes_observed_from_unreviewed() -> None:
    now = datetime.now(UTC)

    def attendance(decisions: list[str]) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            voucher_id=uuid4(),
            performed_by_user_id=uuid4(),
            branch_id=uuid4(),
            attended_at=now,
            voucher=SimpleNamespace(
                purchase_order_id=uuid4(), voucher_number="V-1", issuer_name="Entidad"
            ),
            verifications=[
                SimpleNamespace(decision=decision, reviewed_at=now) for decision in decisions
            ],
        )

    service = VerificationService()
    service.verifications = Mock()
    service.verifications.list_pending.return_value = [attendance([]), attendance(["OBSERVED"])]
    result = service.list_pending(Mock())
    assert [item.verification_status for item in result] == ["PENDING_VERIFICATION", "OBSERVED"]

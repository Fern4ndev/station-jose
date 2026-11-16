"""Administrative verification schema tests."""

import pytest
from app.schemas.verification import VerificationCreate, VerificationDecision
from pydantic import ValidationError


def test_observed_requires_observation() -> None:
    with pytest.raises(ValidationError):
        VerificationCreate(decision=VerificationDecision.OBSERVED)


def test_verified_allows_empty_observation() -> None:
    data = VerificationCreate(decision=VerificationDecision.VERIFIED)

    assert data.decision == VerificationDecision.VERIFIED
    assert data.observation is None


def test_observed_normalizes_observation() -> None:
    data = VerificationCreate(
        decision=VerificationDecision.OBSERVED,
        observation="  Diferencia en el número  ",
    )

    assert data.observation == "Diferencia en el número"

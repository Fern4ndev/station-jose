"""Administrative verification schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class VerificationDecision(StrEnum):
    VERIFIED = "VERIFIED"
    OBSERVED = "OBSERVED"


class VerificationCreate(BaseModel):
    decision: VerificationDecision
    observation: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_observation(self) -> "VerificationCreate":
        if self.decision == VerificationDecision.OBSERVED and not self.observation:
            raise ValueError("La observación es obligatoria cuando el resultado es OBSERVED.")
        if self.observation is not None:
            self.observation = self.observation.strip()
        return self


class VerificationResponse(BaseModel):
    id: UUID
    attendance_id: UUID
    reviewed_by_user_id: UUID
    decision: VerificationDecision
    observation: str | None
    reviewed_at: datetime


class VerificationPendingResponse(BaseModel):
    attendance_id: UUID
    voucher_id: UUID
    purchase_order_id: UUID
    voucher_number: str
    issuer_name: str
    performed_by_user_id: UUID
    branch_id: UUID
    attended_at: datetime
    verification_status: str

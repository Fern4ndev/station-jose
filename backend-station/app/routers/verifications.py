"""Administrative attendance verification endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, require_permission
from app.database import get_db
from app.schemas.verification import (
    VerificationCreate,
    VerificationPendingResponse,
    VerificationResponse,
)
from app.services.verification_service import VerificationService

router = APIRouter(tags=["Verifications"])


@router.get(
    "/verifications/pending",
    response_model=list[VerificationPendingResponse],
    dependencies=[Depends(require_permission("vouchers.verify"))],
)
def list_pending_verifications(
    db: Annotated[Session, Depends(get_db)],
) -> list[VerificationPendingResponse]:
    return VerificationService().list_pending(db)


@router.post(
    "/attendances/{attendance_id}/verifications",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("vouchers.verify"))],
)
def verify_attendance(
    attendance_id: UUID,
    data: VerificationCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> VerificationResponse:
    response = VerificationService().verify(
        db,
        attendance_id,
        data,
        reviewer_id=current_user.id,
    )
    db.commit()
    return response

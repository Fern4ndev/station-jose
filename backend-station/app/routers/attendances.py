"""Attendance endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, require_permission
from app.database import get_db
from app.schemas.attendance import (
    AttendanceResponse,
    FirstAttendanceCreate,
    FollowUpAttendanceCreate,
)
from app.schemas.operational import OperationalAttendance
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendances"])


@router.post(
    "/purchase-orders/{order_id}/attendances",
    response_model=AttendanceResponse | OperationalAttendance,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("attendances.create"))],
)
def create_first_attendance(
    order_id: UUID,
    data: FirstAttendanceCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> AttendanceResponse | JSONResponse:
    response = AttendanceService().create_first(
        db,
        order_id,
        data,
        user_id=current_user.id,
        branch_id=current_user.branch_id,
        idempotency_key=idempotency_key,
    )
    db.commit()
    if current_user.role == "ATTENDANT":
        return JSONResponse(
            OperationalAttendance.model_validate(response).model_dump(mode="json"), status_code=201
        )
    return response


@router.post(
    "/vouchers/{voucher_id}/attendances",
    response_model=AttendanceResponse | OperationalAttendance,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("attendances.create"))],
)
def create_follow_up_attendance(
    voucher_id: UUID,
    data: FollowUpAttendanceCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> AttendanceResponse | JSONResponse:
    response = AttendanceService().create_follow_up(
        db,
        voucher_id,
        data,
        user_id=current_user.id,
        branch_id=current_user.branch_id,
        idempotency_key=idempotency_key,
    )
    db.commit()
    if current_user.role == "ATTENDANT":
        return JSONResponse(
            OperationalAttendance.model_validate(response).model_dump(mode="json"), status_code=201
        )
    return response

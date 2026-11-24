"""Attendance endpoints."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, require_permission
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.core.permissions import permissions_for_role
from app.database import get_db
from app.repositories.attendance_repository import AttendanceRepository
from app.schemas.attendance import (
    AttendanceResponse,
    FirstAttendanceCreate,
    FollowUpAttendanceCreate,
)
from app.schemas.operational import OperationalAttendance
from app.schemas.purchase_order import PaginationResponse
from app.services.attendance_service import AttendanceService
from app.tables import User

router = APIRouter(tags=["Attendances"])


class AttendanceListResponse(BaseModel):
    items: list[AttendanceResponse | OperationalAttendance]
    pagination: PaginationResponse


def _visible_attendances(
    db: Session, user: User, page: int, page_size: int, target_user_id: UUID | None = None
) -> AttendanceListResponse:
    permissions = permissions_for_role(user.role)
    if target_user_id is not None and "attendances.read_all" not in permissions:
        raise PermissionDeniedError("No tiene permiso para consultar otro usuario.")
    if "attendances.read_all" not in permissions and "attendances.read_own" not in permissions:
        raise PermissionDeniedError("No tiene permiso para consultar atenciones.")
    user_id = target_user_id if target_user_id is not None else (
        user.id if "attendances.read_all" not in permissions else None
    )
    rows, total = AttendanceRepository().list(
        db,
        user_id=user_id,
        branch_id=user.branch_id if user.role == "ATTENDANT" else None,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    service = AttendanceService()
    return AttendanceListResponse(
        items=[
            OperationalAttendance.model_validate(service.attendance_response(row))
            if user.role == "ATTENDANT" else service.attendance_response(row)
            for row in rows
        ],
        pagination=PaginationResponse(
            page=page, page_size=page_size, total=total, pages=ceil(total / page_size)
        ),
    )


@router.get("/attendances", response_model=AttendanceListResponse)
def list_attendances(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AttendanceListResponse:
    return _visible_attendances(db, user, page, page_size)


@router.get("/users/{user_id}/attendances", response_model=AttendanceListResponse)
def list_user_attendances(
    user_id: UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AttendanceListResponse:
    return _visible_attendances(db, user, page, page_size, user_id)


@router.get(
    "/attendances/{attendance_id}",
    response_model=AttendanceResponse | OperationalAttendance,
)
def get_attendance(
    attendance_id: UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AttendanceResponse | OperationalAttendance:
    permissions = permissions_for_role(user.role)
    if "attendances.read_all" not in permissions and "attendances.read_own" not in permissions:
        raise PermissionDeniedError("No tiene permiso para consultar atenciones.")
    attendance = AttendanceRepository().get_by_id(db, attendance_id)
    if attendance is None or (
        "attendances.read_all" not in permissions
        and (attendance.performed_by_user_id != user.id or attendance.branch_id != user.branch_id)
    ):
        raise ResourceNotFoundError("Atención no encontrada.")
    response = AttendanceService().attendance_response(attendance)
    return OperationalAttendance.model_validate(response) if user.role == "ATTENDANT" else response


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

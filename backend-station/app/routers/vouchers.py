"""Voucher query endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.attendance import VoucherResponse
from app.schemas.operational import OperationalVoucher, OperationalVoucherList, operational_voucher
from app.schemas.voucher import VoucherDescriptiveUpdate, VoucherListResponse
from app.services.attendance_service import AttendanceService
from app.services.voucher_maintenance_service import VoucherMaintenanceService
from app.tables import User

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


@router.get("", response_model=VoucherListResponse | OperationalVoucherList)
def list_vouchers(
    user: Annotated[User, Depends(require_permission("vouchers.read"))],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    purchase_order_id: Annotated[UUID | None, Query()] = None,
    voucher_number: Annotated[str | None, Query(max_length=60)] = None,
    issuer_name: Annotated[str | None, Query(max_length=200)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> VoucherListResponse | JSONResponse:
    result = AttendanceService().list_vouchers(
        db,
        page=page,
        page_size=page_size,
        purchase_order_id=purchase_order_id,
        voucher_number=voucher_number,
        issuer_name=issuer_name,
        created_from=created_from,
        created_to=created_to,
        branch_id=None,
    )
    if user.role == "ATTENDANT":
        safe = OperationalVoucherList(
            items=[operational_voucher(item, user.id) for item in result.items],
            pagination=result.pagination,
        )
        return JSONResponse(safe.model_dump(mode="json"))
    return result


@router.get(
    "/attended",
    response_model=OperationalVoucherList,
)
def list_attended_vouchers(
    user: Annotated[User, Depends(require_permission("attendances.read_own"))],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    voucher_number: Annotated[str | None, Query(max_length=60)] = None,
) -> OperationalVoucherList:
    result = AttendanceService().list_vouchers(
        db,
        page=page,
        page_size=page_size,
        purchase_order_id=None,
        voucher_number=voucher_number,
        issuer_name=None,
        created_from=None,
        created_to=None,
        attended_by_user_id=user.id,
        branch_id=None,
    )
    return OperationalVoucherList(
        items=[operational_voucher(item, user.id) for item in result.items],
        pagination=result.pagination,
    )


@router.get("/{voucher_id}", response_model=VoucherResponse | OperationalVoucher)
def get_voucher(
    voucher_id: UUID,
    user: Annotated[User, Depends(require_permission("vouchers.read"))],
    db: Annotated[Session, Depends(get_db)],
) -> VoucherResponse | JSONResponse:
    result = AttendanceService().get_voucher(
        db,
        voucher_id,
        branch_id=None,
    )
    if user.role == "ATTENDANT":
        return JSONResponse(operational_voucher(result, user.id).model_dump(mode="json"))
    return result


@router.patch(
    "/{voucher_id}/descriptive-data",
    response_model=VoucherResponse,
    dependencies=[Depends(require_permission("vouchers.correct_descriptive"))],
)
def correct_voucher(
    voucher_id: UUID,
    data: VoucherDescriptiveUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> VoucherResponse:
    response = VoucherMaintenanceService().correct_voucher(db, voucher_id, data)
    db.commit()
    return response


@router.delete(
    "/{voucher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("vouchers.delete"))],
)
def delete_voucher(
    voucher_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    VoucherMaintenanceService().delete_voucher(db, voucher_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Voucher query endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.attendance import VoucherResponse
from app.schemas.voucher import VoucherListResponse
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


@router.get("", response_model=VoucherListResponse)
def list_vouchers(
    _: Annotated[object, Depends(require_permission("vouchers.read"))],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    purchase_order_id: Annotated[UUID | None, Query()] = None,
    voucher_number: Annotated[str | None, Query(max_length=60)] = None,
    issuer_name: Annotated[str | None, Query(max_length=200)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> VoucherListResponse:
    return AttendanceService().list_vouchers(
        db,
        page=page,
        page_size=page_size,
        purchase_order_id=purchase_order_id,
        voucher_number=voucher_number,
        issuer_name=issuer_name,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/{voucher_id}", response_model=VoucherResponse)
def get_voucher(
    voucher_id: UUID,
    _: Annotated[object, Depends(require_permission("vouchers.read"))],
    db: Annotated[Session, Depends(get_db)],
) -> VoucherResponse:
    return AttendanceService().get_voucher(db, voucher_id)

"""Read-only balances derived from confirmed attendances."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.purchase_order import PaginationResponse
from app.services.attendance_service import AttendanceService
from app.services.purchase_order_service import PurchaseOrderService
from app.tables import User

router = APIRouter(prefix="/balances", tags=["Balances"])


class BalanceLine(BaseModel):
    id: UUID
    fuel_type: str
    authorized_gallons: Decimal
    attended_gallons: Decimal
    available_gallons: Decimal
    status: str


class DocumentBalance(BaseModel):
    id: UUID
    number: str
    status: str
    items: list[BalanceLine]


class BalanceOverview(BaseModel):
    items: list[DocumentBalance]
    pagination: PaginationResponse


@router.get("/purchase-orders/{order_id}", response_model=DocumentBalance)
def purchase_order_balance(
    order_id: UUID,
    user: Annotated[User, Depends(require_permission("balances.read"))],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentBalance:
    order = PurchaseOrderService().get(
        db, order_id, branch_id=None
    )
    return DocumentBalance(
        id=order.id,
        number=order.order_number,
        status=order.status,
        items=[
            BalanceLine(
                id=item.id,
                fuel_type=item.fuel_type.name,
                authorized_gallons=item.authorized_gallons,
                attended_gallons=item.attended_gallons,
                available_gallons=item.available_gallons,
                status=item.status,
            )
            for item in order.items
        ],
    )


@router.get("/vouchers/{voucher_id}", response_model=DocumentBalance)
def voucher_balance(
    voucher_id: UUID,
    user: Annotated[User, Depends(require_permission("balances.read"))],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentBalance:
    voucher = AttendanceService().get_voucher(
        db, voucher_id, branch_id=None
    )
    order = PurchaseOrderService().get(
        db, voucher.purchase_order_id,
        branch_id=None,
    )
    fuel_by_order_item = {item.id: item.fuel_type.name for item in order.items}
    return DocumentBalance(
        id=voucher.id,
        number=voucher.voucher_number,
        status=voucher.status,
        items=[
            BalanceLine(
                id=item.id,
                fuel_type=fuel_by_order_item.get(item.purchase_order_item_id, ""),
                authorized_gallons=item.authorized_gallons,
                attended_gallons=item.attended_gallons,
                available_gallons=item.available_gallons,
                status=item.status,
            )
            for item in voucher.items
        ],
    )


@router.get("/overview", response_model=BalanceOverview)
def balance_overview(
    user: Annotated[User, Depends(require_permission("balances.read"))],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BalanceOverview:
    orders = PurchaseOrderService().list(
        db,
        page=page,
        page_size=page_size,
        search=None,
        branch_id=None,
        issue_date_from=None,
        issue_date_to=None,
        sort_by="issue_date",
        sort_order="desc",
    )
    items = [
        DocumentBalance(
            id=order.id,
            number=order.order_number,
            status=order.status,
            items=[
                BalanceLine(
                    id=item.id,
                    fuel_type=item.fuel_type.name,
                    authorized_gallons=item.authorized_gallons,
                    attended_gallons=item.attended_gallons,
                    available_gallons=item.available_gallons,
                    status=item.status,
                )
                for item in order.items
            ],
        )
        for order in orders.items
    ]
    return BalanceOverview(items=items, pagination=orders.pagination)

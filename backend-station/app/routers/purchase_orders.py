"""Purchase order endpoints."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.database import get_db
from app.schemas.operational import OperationalOrder, OperationalOrderList
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.services.purchase_order_service import PurchaseOrderService
from app.tables import User

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


@router.get("", response_model=PurchaseOrderListResponse | OperationalOrderList)
def list_purchase_orders(
    user: Annotated[User, Depends(require_permission("purchase_orders.read"))],
    db: Annotated[Session, Depends(get_db)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    issue_date_from: Annotated[date | None, Query()] = None,
    issue_date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Annotated[
        Literal["issue_date", "order_number", "institution_name"], Query()
    ] = "issue_date",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> PurchaseOrderListResponse | JSONResponse:
    result = PurchaseOrderService().list(
        db,
        page=page,
        page_size=page_size,
        search=search,
        branch_id=user.branch_id if user.role == "ATTENDANT" else branch_id,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if user.role == "ATTENDANT":
        return JSONResponse(OperationalOrderList.model_validate(result).model_dump(mode="json"))
    return result


@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("purchase_orders.create"))],
)
def create_purchase_order(
    data: PurchaseOrderCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PurchaseOrderResponse:
    order = PurchaseOrderService().create(db, data)
    db.commit()
    return order


@router.get("/{order_id}", response_model=PurchaseOrderResponse | OperationalOrder)
def get_purchase_order(
    order_id: UUID,
    user: Annotated[User, Depends(require_permission("purchase_orders.read"))],
    db: Annotated[Session, Depends(get_db)],
) -> PurchaseOrderResponse | JSONResponse:
    result = PurchaseOrderService().get(
        db,
        order_id,
        branch_id=user.branch_id if user.role == "ATTENDANT" else None,
    )
    if user.role == "ATTENDANT":
        return JSONResponse(OperationalOrder.model_validate(result).model_dump(mode="json"))
    return result


@router.patch(
    "/{order_id}",
    response_model=PurchaseOrderResponse,
    dependencies=[Depends(require_permission("purchase_orders.update"))],
)
def update_purchase_order(
    order_id: UUID,
    data: PurchaseOrderUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PurchaseOrderResponse:
    order = PurchaseOrderService().update(db, order_id, data)
    db.commit()
    return order


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("purchase_orders.delete"))],
)
def delete_purchase_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    PurchaseOrderService().delete(db, order_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

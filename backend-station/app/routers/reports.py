"""Operational report and dashboard endpoints."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.core.exceptions import InvalidReportFilterError
from app.database import get_db
from app.schemas.report import (
    AttendanceReportResponse,
    DashboardResponse,
    PurchaseOrderReportResponse,
    ReportFilters,
    ReportGrouping,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])
dashboard_router = APIRouter(tags=["Dashboard"])


def _filters(
    date_from: date | None,
    date_to: date | None,
    user_id: UUID | None,
    branch_id: UUID | None,
    status: str | None,
    group_by: ReportGrouping,
    hour_from: int = 0,
    hour_to: int = 23,
) -> ReportFilters:
    if date_from and date_to and date_from > date_to:
        raise InvalidReportFilterError("date_from no puede ser posterior a date_to.")
    if hour_from > hour_to:
        raise InvalidReportFilterError("La hora desde no puede ser posterior a la hora hasta.")
    return ReportFilters(
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        branch_id=branch_id,
        status=status,
        group_by=group_by,
        hour_from=hour_from,
        hour_to=hour_to,
    )


@router.get(
    "/purchase-orders",
    response_model=PurchaseOrderReportResponse,
    dependencies=[Depends(require_permission("reports.read"))],
)
def purchase_order_report(
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> PurchaseOrderReportResponse:
    return ReportService().purchase_orders(
        db,
        _filters(date_from, date_to, None, branch_id, status, ReportGrouping.DAY),
    )


@router.get(
    "/attendances",
    response_model=AttendanceReportResponse,
    dependencies=[Depends(require_permission("reports.read"))],
)
def attendance_report(
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    hour_from: Annotated[int, Query(ge=0, le=23)] = 0,
    hour_to: Annotated[int, Query(ge=0, le=23)] = 23,
) -> AttendanceReportResponse:
    return ReportService().attendances(
        db,
        _filters(
            date_from, date_to, user_id, branch_id, None, ReportGrouping.DAY, hour_from, hour_to
        ),
    )


@dashboard_router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("reports.read"))],
)
@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("reports.read"))],
)
def dashboard_report(
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
    group_by: Annotated[ReportGrouping, Query()] = ReportGrouping.DAY,
    hour_from: Annotated[int, Query(ge=0, le=23)] = 0,
    hour_to: Annotated[int, Query(ge=0, le=23)] = 23,
) -> DashboardResponse:
    return ReportService().dashboard(
        db,
        _filters(date_from, date_to, user_id, branch_id, status, group_by, hour_from, hour_to),
    )


@router.get(
    "/purchase-orders/export",
    dependencies=[Depends(require_permission("reports.export"))],
)
def export_purchase_order_report(
    db: Annotated[Session, Depends(get_db)],
    file_format: Annotated[Literal["pdf", "xlsx"], Query(alias="format")],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
) -> Response:
    content, media_type, filename = ReportService().export_purchase_orders(
        db,
        _filters(date_from, date_to, None, branch_id, None, ReportGrouping.DAY),
        file_format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/attendances/export",
    dependencies=[Depends(require_permission("reports.export"))],
)
def export_attendance_report(
    db: Annotated[Session, Depends(get_db)],
    file_format: Annotated[Literal["pdf", "xlsx"], Query(alias="format")],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    branch_id: Annotated[UUID | None, Query()] = None,
    hour_from: Annotated[int, Query(ge=0, le=23)] = 0,
    hour_to: Annotated[int, Query(ge=0, le=23)] = 23,
) -> Response:
    content, media_type, filename = ReportService().export_attendances(
        db,
        _filters(
            date_from, date_to, user_id, branch_id, None, ReportGrouping.DAY, hour_from, hour_to
        ),
        file_format,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

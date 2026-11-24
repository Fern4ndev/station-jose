"""Report queries, aggregation and export datasets."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.repositories.balance_repository import BalanceRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    AttendanceReportResponse,
    AttendanceReportRow,
    DashboardResponse,
    FuelDashboardRow,
    PeriodDashboardRow,
    PurchaseOrderReportResponse,
    PurchaseOrderReportRow,
    ReportFilters,
)


class ReportExportUnavailableError(AppError):
    status_code = 503
    code = "REPORT_EXPORT_UNAVAILABLE"


class ReportExportLimitError(AppError):
    status_code = 413
    code = "REPORT_EXPORT_LIMIT_EXCEEDED"


class ReportService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.reports = ReportRepository()
        self.balances = BalanceRepository()

    def purchase_orders(self, db: Session, filters: ReportFilters) -> PurchaseOrderReportResponse:
        orders = self.reports.list_purchase_orders(
            db,
            date_from=filters.date_from,
            date_to=filters.date_to,
            branch_id=filters.branch_id,
        )
        item_ids = [item.id for order in orders for item in order.items]
        consumed = self.balances.consumed_by_order_items(db, item_ids)
        rows: list[PurchaseOrderReportRow] = []
        for order in orders:
            for item in order.items:
                attended = consumed.get(item.id, Decimal("0"))
                available = item.authorized_gallons - attended
                status = "AVAILABLE" if available > 0 else "DEPLETED"
                if filters.status and filters.status != status:
                    continue
                rows.append(
                    PurchaseOrderReportRow(
                        order_id=order.id,
                        order_number=order.order_number,
                        institution_name=order.institution_name,
                        branch_name=order.branch.name,
                        issue_date=order.issue_date,
                        fuel_type_code=item.fuel_type.code,
                        fuel_type_name=item.fuel_type.name,
                        authorized_gallons=item.authorized_gallons,
                        attended_gallons=attended,
                        available_gallons=available,
                        status=status,
                        unit_price=item.unit_price,
                        total_amount=item.total_amount,
                    )
                )
        return PurchaseOrderReportResponse(
            generated_at=datetime.now(UTC),
            filters=filters,
            items=rows,
            total=len(rows),
        )

    def attendances(self, db: Session, filters: ReportFilters) -> AttendanceReportResponse:
        attendances = self.reports.list_attendances(
            db,
            date_from=filters.date_from,
            date_to=filters.date_to,
            user_id=filters.user_id,
            branch_id=filters.branch_id,
        )
        rows: list[AttendanceReportRow] = []
        for attendance in attendances:
            for item in attendance.items:
                order_item = item.voucher_item.purchase_order_item
                if order_item is None:
                    continue
                rows.append(
                    AttendanceReportRow(
                        attendance_id=attendance.id,
                        voucher_id=attendance.voucher_id,
                        voucher_number=attendance.voucher.voucher_number,
                        order_id=order_item.purchase_order_id,
                        order_number=order_item.purchase_order.order_number,
                        attended_at=attendance.attended_at,
                        performed_by_user_id=attendance.performed_by_user_id,
                        performer_name=(
                            f"{attendance.performed_by.first_name} "
                            f"{attendance.performed_by.last_name}"
                        ),
                        branch_name=attendance.branch.name,
                        fuel_type_code=order_item.fuel_type.code,
                        fuel_type_name=order_item.fuel_type.name,
                        attended_gallons=item.attended_gallons,
                        unit_price=item.unit_price_snapshot,
                        attended_amount=item.attended_amount,
                    )
                )
        return AttendanceReportResponse(
            generated_at=datetime.now(UTC),
            filters=filters,
            items=rows,
            total=len(rows),
        )

    def dashboard(self, db: Session, filters: ReportFilters) -> DashboardResponse:
        order_report = self.purchase_orders(db, filters)
        attendance_report = self.attendances(db, filters)
        fuel: dict[tuple[str, str], list[Decimal]] = defaultdict(lambda: [Decimal("0")] * 4)
        periods: dict[str, list[Decimal | int]] = defaultdict(
            lambda: [Decimal("0"), Decimal("0"), 0]
        )
        for order_row in order_report.items:
            values = fuel[(order_row.fuel_type_code, order_row.fuel_type_name)]
            values[0] += order_row.authorized_gallons
            values[1] += order_row.attended_gallons
            values[2] += order_row.available_gallons
        for attendance_row in attendance_report.items:
            values = fuel[(attendance_row.fuel_type_code, attendance_row.fuel_type_name)]
            values[3] += attendance_row.attended_amount
            period = _period_key(attendance_row.attended_at, filters.group_by.value)
            periods[period][0] += attendance_row.attended_gallons
            periods[period][1] += attendance_row.attended_amount
            periods[period][2] += 1
        order_ids = {row.order_id for row in order_report.items}
        voucher_ids = {row.voucher_id for row in attendance_report.items}
        attendance_ids = {row.attendance_id for row in attendance_report.items}
        return DashboardResponse(
            generated_at=datetime.now(UTC),
            filters=filters,
            orders=len(order_ids),
            vouchers=len(voucher_ids),
            attendances=len(attendance_ids),
            authorized_gallons=sum(
                (row.authorized_gallons for row in order_report.items), Decimal("0")
            ),
            attended_gallons=sum(
                (row.attended_gallons for row in attendance_report.items), Decimal("0")
            ),
            available_gallons=sum(
                (row.available_gallons for row in order_report.items), Decimal("0")
            ),
            attended_amount=sum(
                (row.attended_amount for row in attendance_report.items), Decimal("0")
            ),
            by_fuel=[
                FuelDashboardRow(
                    fuel_type_code=code,
                    fuel_type_name=name,
                    authorized_gallons=values[0],
                    attended_gallons=values[1],
                    available_gallons=values[2],
                    attended_amount=values[3],
                )
                for (code, name), values in sorted(fuel.items())
            ],
            by_period=[
                PeriodDashboardRow(
                    period=period,
                    attended_gallons=values[0],
                    attended_amount=values[1],
                    attendances=values[2],
                )
                for period, values in sorted(periods.items())
            ],
        )

    def export_purchase_orders(
        self, db: Session, filters: ReportFilters, file_format: str
    ) -> tuple[bytes, str, str]:
        report = self.purchase_orders(db, filters)
        self._validate_export_size(report.total)
        return _export_rows(
            [row.model_dump(mode="json") for row in report.items],
            "purchase-orders",
            file_format,
        )

    def export_attendances(
        self, db: Session, filters: ReportFilters, file_format: str
    ) -> tuple[bytes, str, str]:
        report = self.attendances(db, filters)
        self._validate_export_size(report.total)
        return _export_rows(
            [row.model_dump(mode="json") for row in report.items],
            "attendances",
            file_format,
        )

    def _validate_export_size(self, total: int) -> None:
        if total > self.settings.REPORT_MAX_EXPORT_ROWS:
            raise ReportExportLimitError(
                "El reporte supera el máximo de filas exportables.",
                details={"max_rows": self.settings.REPORT_MAX_EXPORT_ROWS},
            )


def _period_key(value: datetime, grouping: str) -> str:
    value = value.astimezone(ZoneInfo(get_settings().TIMEZONE))
    if grouping == "hour":
        return value.strftime("%Y-%m-%d %H:00")
    if grouping == "week":
        year, week, _ = value.isocalendar()
        return f"{year}-W{week:02d}"
    if grouping == "month":
        return value.strftime("%Y-%m")
    return value.strftime("%Y-%m-%d")


def _export_rows(
    rows: list[dict[str, object]], name: str, file_format: str
) -> tuple[bytes, str, str]:
    if file_format == "xlsx":
        return _export_xlsx(rows, name)
    if file_format == "pdf":
        return _export_pdf(rows, name)
    raise ReportExportUnavailableError("Formato de exportación no soportado.")


def _export_xlsx(rows: list[dict[str, object]], name: str) -> tuple[bytes, str, str]:
    try:
        from openpyxl import Workbook  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ReportExportUnavailableError(
            "La exportación XLSX requiere instalar openpyxl."
        ) from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte"
    headers = list(rows[0]) if rows else []
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    stream = BytesIO()
    workbook.save(stream)
    return (
        stream.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{name}.xlsx",
    )


def _export_pdf(rows: list[dict[str, object]], name: str) -> tuple[bytes, str, str]:
    try:
        from reportlab.lib import colors  # type: ignore[import-untyped]
        from reportlab.lib.pagesizes import landscape, letter  # type: ignore[import-untyped]
        from reportlab.platypus import (  # type: ignore[import-untyped]
            SimpleDocTemplate,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise ReportExportUnavailableError(
            "La exportación PDF requiere instalar reportlab."
        ) from exc
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=landscape(letter))
    headers = list(rows[0]) if rows else ["resultado"]
    data = [headers] + [[str(row.get(header, "")) for header in headers] for row in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]
        )
    )
    document.build([table])
    return stream.getvalue(), "application/pdf", f"{name}.pdf"

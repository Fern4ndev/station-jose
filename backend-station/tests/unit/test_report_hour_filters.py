"""Applied report hours use the same Lima interval for queries and exports."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.core.exceptions import InvalidReportFilterError
from app.routers.reports import _filters
from app.schemas.report import ReportFilters, ReportGrouping
from app.services.report_service import ReportService


def _attendance(hour: int, minute: int = 0) -> SimpleNamespace:
    order_item = SimpleNamespace(
        purchase_order_id=uuid4(),
        purchase_order=SimpleNamespace(order_number="OC-001"),
        fuel_type=SimpleNamespace(code="DB5", name="Diésel"),
    )
    item = SimpleNamespace(
        voucher_item=SimpleNamespace(purchase_order_item=order_item),
        attended_gallons=Decimal("10"),
        unit_price_snapshot=Decimal("15"),
        attended_amount=Decimal("150"),
    )
    return SimpleNamespace(
        id=uuid4(),
        voucher_id=uuid4(),
        voucher=SimpleNamespace(voucher_number="V-001"),
        attended_at=datetime(2026, 11, 23, hour, minute, tzinfo=UTC),
        performed_by_user_id=uuid4(),
        performed_by=SimpleNamespace(first_name="Ana", last_name="Pérez"),
        branch=SimpleNamespace(name="San José"),
        items=[item],
    )


def test_hour_filter_includes_the_full_lima_hour_and_filters_export(monkeypatch) -> None:
    service = ReportService()
    service.reports.list_attendances = Mock(
        return_value=[_attendance(12, 59), _attendance(13), _attendance(13, 59), _attendance(14)]
    )
    filters = ReportFilters(hour_from=8, hour_to=8)

    report = service.attendances(Mock(), filters)

    assert report.total == 2
    assert [row.attended_at.hour for row in report.items] == [13, 13]
    captured = []

    def export(rows, name, file_format):
        captured.extend(rows)
        return b"export", "application/octet-stream", "report.xlsx"

    monkeypatch.setattr("app.services.report_service._export_rows", export)
    service.export_attendances(Mock(), filters, "xlsx")
    assert len(captured) == 2


def test_reversed_hours_are_rejected() -> None:
    with pytest.raises(InvalidReportFilterError):
        _filters(None, None, None, None, None, ReportGrouping.DAY, 18, 8)


def test_default_hours_keep_all_attendances() -> None:
    service = ReportService()
    service.reports.list_attendances = Mock(return_value=[_attendance(0), _attendance(23)])
    assert service.attendances(Mock(), ReportFilters()).total == 2

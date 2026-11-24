"""Business-day reports use Lima time at the UTC boundary."""

from datetime import UTC, date, datetime

from app.repositories.report_repository import _start_of_day
from app.services.report_service import _period_key


def test_lima_day_starts_at_five_utc() -> None:
    assert _start_of_day(date(2026, 11, 24)) == datetime(2026, 11, 24, 5, tzinfo=UTC)


def test_period_bucket_uses_lima_calendar_day() -> None:
    value = datetime(2026, 11, 24, 2, 30, tzinfo=UTC)
    assert _period_key(value, "day") == "2026-11-23"
    assert _period_key(value, "hour") == "2026-11-23 21:00"

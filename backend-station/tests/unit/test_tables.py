"""Database metadata and integrity declaration tests."""

import app.tables  # noqa: F401
from app.database import Base


def test_all_phase_two_tables_are_declared() -> None:
    expected = {
        "branches",
        "users",
        "auth_sessions",
        "fuel_types",
        "purchase_orders",
        "purchase_order_items",
        "vouchers",
        "voucher_items",
        "attendances",
        "attendance_items",
        "document_counters",
    }

    assert expected.issubset(Base.metadata.tables)


def test_operational_tables_have_no_delete_cascade() -> None:
    for table_name in ("purchase_orders", "vouchers", "attendances"):
        table = Base.metadata.tables[table_name]
        assert all(foreign_key.ondelete != "CASCADE" for foreign_key in table.foreign_keys)

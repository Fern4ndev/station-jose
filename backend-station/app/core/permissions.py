"""Versioned role-to-permission policy."""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    OFFICE = "OFFICE"
    ATTENDANT = "ATTENDANT"


PERMISSIONS_BY_ROLE: dict[UserRole, frozenset[str]] = {
    UserRole.ADMIN: frozenset(
        {
            "users.manage",
            "purchase_orders.read",
            "purchase_orders.create",
            "purchase_orders.update",
            "purchase_orders.delete",
            "vouchers.read",
            "vouchers.correct_descriptive",
            "vouchers.delete",
            "balances.read",
            "reports.read",
            "reports.export",
            "ocr.purchase_orders.process",
        }
    ),
    UserRole.OFFICE: frozenset(
        {
            "purchase_orders.read",
            "purchase_orders.create",
            "purchase_orders.update",
            "purchase_orders.delete",
            "vouchers.read",
            "vouchers.delete",
            "attendances.read_all",
            "balances.read",
            "reports.read",
            "reports.export",
            "ocr.purchase_orders.process",
        }
    ),
    UserRole.ATTENDANT: frozenset(
        {
            "purchase_orders.read",
            "vouchers.read",
            "attendances.create",
            "attendances.read_own",
            "balances.read",
        }
    ),
}


def permissions_for_role(role: UserRole | str) -> frozenset[str]:
    return PERMISSIONS_BY_ROLE[UserRole(role)]

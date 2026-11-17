"""Transactional voucher attendance use cases."""

import hashlib
import json
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import (
    IdempotencyConflictError,
    InsufficientOrderBalanceError,
    InsufficientVoucherBalanceError,
    InvalidFuelLineError,
    ResourceNotFoundError,
    VoucherAlreadyExistsError,
)
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.balance_repository import BalanceRepository
from app.repositories.voucher_repository import VoucherRepository
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceItemCreate,
    AttendanceResponse,
    FirstAttendanceCreate,
    VoucherItemDetailResponse,
    VoucherResponse,
)
from app.schemas.balance import BalanceStatus
from app.schemas.purchase_order import PaginationResponse
from app.schemas.verification import VerificationDecision, VerificationResponse
from app.schemas.voucher import VoucherListResponse
from app.tables import Attendance, AttendanceItem, PurchaseOrderItem, Voucher, VoucherItem


class AttendanceService:
    def __init__(self) -> None:
        self.vouchers = VoucherRepository()
        self.attendances = AttendanceRepository()
        self.balances = BalanceRepository()

    def create_first(
        self,
        db: Session,
        order_id: UUID,
        data: FirstAttendanceCreate,
        *,
        user_id: UUID,
        branch_id: UUID | None,
        idempotency_key: UUID,
    ) -> AttendanceResponse:
        existing = self._resolve_idempotency(db, idempotency_key, data, user_id=user_id, order_id=order_id)
        if existing is not None:
            return self._attendance_response(existing)

        item_ids = [item.purchase_order_item_id for item in data.items]
        order_items = self.vouchers.lock_items(db, [item_id for item_id in item_ids if item_id])
        by_id = {item.id: item for item in order_items}
        if len(by_id) != len(set(item_ids)):
            raise ResourceNotFoundError("Una o más líneas de la orden no existen.")
        if any(item.purchase_order_id != order_id for item in order_items):
            raise InvalidFuelLineError("Todas las líneas deben pertenecer a la orden indicada.")

        normalized_issuer = normalize_identity(data.issuer_name)
        normalized_number = normalize_identity(data.voucher_number)
        duplicate = self.vouchers.get_duplicate(
            db,
            purchase_order_id=order_id,
            issuer_normalized=normalized_issuer,
            voucher_number_normalized=normalized_number,
        )
        if duplicate is not None:
            raise VoucherAlreadyExistsError(
                "Ya existe un vale con esos datos para la orden.",
                details={"voucher_id": str(duplicate.id)},
            )

        self._validate_order_balance(db, data.items, by_id)
        voucher = Voucher(
            id=uuid4(),
            purchase_order_id=order_id,
            issuer_type=data.issuer_type,
            issuer_name=data.issuer_name.strip(),
            issuer_normalized=normalized_issuer,
            voucher_number=data.voucher_number.strip(),
            voucher_number_normalized=normalized_number,
        )
        db.add(voucher)
        db.flush()
        voucher_items = [
            VoucherItem(
                id=uuid4(),
                voucher_id=voucher.id,
                purchase_order_id=order_id,
                purchase_order_item_id=item.purchase_order_item_id,
                authorized_gallons=item.attended_gallons,
            )
            for item in data.items
            if item.purchase_order_item_id is not None
        ]
        voucher.items = voucher_items
        db.flush()
        attendance = self._insert_attendance(
            db,
            voucher,
            voucher_items,
            data.items,
            user_id=user_id,
            branch_id=branch_id or self._order_branch_id(order_items),
            idempotency_key=idempotency_key,
            fingerprint=fingerprint(data),
            prices=by_id,
        )
        db.flush()
        return self._attendance_response(attendance)

    def create_follow_up(
        self,
        db: Session,
        voucher_id: UUID,
        data: AttendanceCreate,
        *,
        user_id: UUID,
        branch_id: UUID | None,
        idempotency_key: UUID,
    ) -> AttendanceResponse:
        existing = self._resolve_idempotency(db, idempotency_key, data, user_id=user_id, voucher_id=voucher_id)
        if existing is not None:
            return self._attendance_response(existing)
        item_ids = [item.voucher_item_id for item in data.items]
        order_item_ids = self.vouchers.order_item_ids_for_voucher(db, voucher_id)
        locked_order_items = self.vouchers.lock_items(db, order_item_ids)
        voucher = self.vouchers.lock_voucher(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")
        voucher_items = self.vouchers.lock_voucher_items(
            db, [item_id for item_id in item_ids if item_id]
        )
        by_id = {item.id: item for item in voucher_items}
        if len(by_id) != len(set(item_ids)):
            raise ResourceNotFoundError("Una o más líneas del vale no existen.")
        if any(item.voucher_id != voucher_id for item in voucher_items):
            raise InvalidFuelLineError("Todas las líneas deben pertenecer al vale indicado.")
        self._validate_voucher_balance(db, data.items, by_id)
        order_items_by_id = {item.id: item for item in locked_order_items}
        prices = {
            item.id: order_items_by_id[item.purchase_order_item_id]
            for item in voucher_items
            if item.purchase_order_item_id in order_items_by_id
        }
        attendance = self._insert_attendance(
            db,
            voucher,
            voucher_items,
            data.items,
            user_id=user_id,
            branch_id=branch_id or self._order_branch_id(locked_order_items),
            idempotency_key=idempotency_key,
            fingerprint=fingerprint(data),
            prices=prices,
        )
        db.flush()
        return self._attendance_response(attendance)

    def get_voucher(self, db: Session, voucher_id: UUID) -> VoucherResponse:
        voucher = self.vouchers.get_by_id(db, voucher_id)
        if voucher is None:
            raise ResourceNotFoundError("Vale no encontrado.")
        return self._voucher_response(db, voucher)

    def list_vouchers(
        self,
        db: Session,
        *,
        page: int,
        page_size: int,
        purchase_order_id: UUID | None,
        voucher_number: str | None,
        issuer_name: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> VoucherListResponse:
        vouchers, total = self.vouchers.list(
            db,
            purchase_order_id=purchase_order_id,
            voucher_number=voucher_number,
            issuer_name=issuer_name,
            created_from=created_from,
            created_to=created_to,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return VoucherListResponse(
            items=[self._voucher_response(db, voucher) for voucher in vouchers],
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                pages=(total + page_size - 1) // page_size if total else 0,
            ),
        )

    def _resolve_idempotency(
        self, db: Session, key: UUID, data: AttendanceCreate, *, user_id: UUID,
        order_id: UUID | None = None, voucher_id: UUID | None = None,
    ) -> Attendance | None:
        existing = self.vouchers.get_attendance_by_idempotency(db, key)
        if existing is None:
            return None
        if (
            existing.request_fingerprint != fingerprint(data)
            or existing.performed_by_user_id != user_id
            or (voucher_id is not None and existing.voucher_id != voucher_id)
            or (order_id is not None and existing.voucher.purchase_order_id != order_id)
        ):
            raise IdempotencyConflictError(
                "La clave de idempotencia ya fue utilizada con otro contenido.",
                details={"attendance_id": str(existing.id)},
            )
        return existing

    def _validate_order_balance(
        self,
        db: Session,
        requested: list[AttendanceItemCreate],
        items: dict[UUID, PurchaseOrderItem],
    ) -> None:
        consumed = self.balances.consumed_by_order_items(db, items)
        for line in requested:
            assert line.purchase_order_item_id is not None
            order_item = items[line.purchase_order_item_id]
            available = order_item.authorized_gallons - consumed.get(order_item.id, Decimal("0"))
            if line.attended_gallons > available:
                raise InsufficientOrderBalanceError(
                    "El despacho supera el saldo disponible de la línea de la orden.",
                    details={"purchase_order_item_id": str(order_item.id)},
                )

    def _validate_voucher_balance(
        self,
        db: Session,
        requested: list[AttendanceItemCreate],
        items: dict[UUID, VoucherItem],
    ) -> None:
        consumed = self.balances.consumed_by_voucher_items(db, items)
        for line in requested:
            voucher_item_id = line.voucher_item_id
            assert voucher_item_id is not None
            voucher_item = items[voucher_item_id]
            available = voucher_item.authorized_gallons - consumed.get(
                voucher_item.id, Decimal("0")
            )
            if line.attended_gallons > available:
                raise InsufficientVoucherBalanceError(
                    "El despacho supera el saldo disponible del vale.",
                    details={"voucher_item_id": str(voucher_item.id)},
                )
        order_requests: list[AttendanceItemCreate] = []
        order_items: dict[UUID, PurchaseOrderItem] = {}
        for line in requested:
            voucher_item_id = line.voucher_item_id
            assert voucher_item_id is not None
            voucher_item = items[voucher_item_id]
            order_item = voucher_item.purchase_order_item
            if order_item is None:
                raise InvalidFuelLineError("La línea no tiene una línea de orden válida.")
            order_items[order_item.id] = order_item
            order_requests.append(
                AttendanceItemCreate(
                    purchase_order_item_id=order_item.id,
                    attended_gallons=line.attended_gallons,
                )
            )
        self._validate_order_balance(db, order_requests, order_items)

    def _insert_attendance(
        self,
        db: Session,
        voucher: Voucher,
        voucher_items: list[VoucherItem],
        requested: list[AttendanceItemCreate],
        *,
        user_id: UUID,
        branch_id: UUID,
        idempotency_key: UUID,
        fingerprint: str,
        prices: dict[UUID, PurchaseOrderItem],
    ) -> Attendance:
        voucher_by_order = {item.purchase_order_item_id: item for item in voucher_items}
        voucher_by_id = {item.id: item for item in voucher_items}
        attendance = Attendance(
            id=uuid4(),
            voucher_id=voucher.id,
            performed_by_user_id=user_id,
            branch_id=branch_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        attendance.items = []
        for line in requested:
            if line.voucher_item_id is not None:
                voucher_item = voucher_by_id[line.voucher_item_id]
            else:
                purchase_order_item_id = line.purchase_order_item_id
                assert purchase_order_item_id is not None
                voucher_item = voucher_by_order[purchase_order_item_id]
            order_item = (
                prices[voucher_item.id]
                if voucher_item.id in prices
                else voucher_item.purchase_order_item
            )
            if order_item is None:
                raise InvalidFuelLineError("La línea no tiene una línea de orden válida.")
            amount = (line.attended_gallons * order_item.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            attendance.items.append(
                AttendanceItem(
                    id=uuid4(),
                    attendance_id=attendance.id,
                    voucher_id=voucher.id,
                    voucher_item_id=voucher_item.id,
                    attended_gallons=line.attended_gallons,
                    unit_price_snapshot=order_item.unit_price,
                    attended_amount=amount,
                )
            )
        db.add(attendance)
        return attendance

    def _attendance_response(self, attendance: Attendance) -> AttendanceResponse:
        response = AttendanceResponse.model_validate(attendance, from_attributes=True)
        response.verifications = [
            VerificationResponse.model_validate(item, from_attributes=True)
            for item in attendance.verifications
        ]
        return response

    def _voucher_response(self, db: Session, voucher: Voucher) -> VoucherResponse:
        item_ids = [item.id for item in voucher.items]
        consumed = self.balances.consumed_by_voucher_items(db, item_ids)
        order_item_ids = [item.purchase_order_item_id for item in voucher.items]
        order_consumed = self.balances.consumed_by_order_items(db, order_item_ids)
        detail_items = []
        for item in voucher.items:
            attended = consumed.get(item.id, Decimal("0"))
            available = item.authorized_gallons - attended
            order_item = item.purchase_order_item
            order_available = None
            if order_item is not None:
                order_available = order_item.authorized_gallons - order_consumed.get(
                    order_item.id, Decimal("0")
                )
            detail_items.append(
                VoucherItemDetailResponse(
                    id=item.id,
                    purchase_order_item_id=item.purchase_order_item_id,
                    authorized_gallons=item.authorized_gallons,
                    attended_gallons=attended,
                    available_gallons=available,
                    status=_item_status(item.authorized_gallons, attended, order_available),
                )
            )
        statuses = [item.status for item in detail_items]
        status = (
            "COMPLETED"
            if statuses and all(value == "COMPLETED" for value in statuses)
            else (
                "PENDING"
                if statuses and all(value == "PENDING" for value in statuses)
                else (
                    "PARTIALLY_BLOCKED"
                    if any(value == "BLOCKED_BY_ORDER_BALANCE" for value in statuses)
                    else "PARTIALLY_ATTENDED"
                )
            )
        )
        return VoucherResponse(
            id=voucher.id,
            purchase_order_id=voucher.purchase_order_id,
            issuer_type=voucher.issuer_type,
            issuer_name=voucher.issuer_name,
            voucher_number=voucher.voucher_number,
            created_at=voucher.created_at,
            status=status,
            verification_status=_voucher_verification_status(voucher),
            items=detail_items,
            attendances=[
                self._attendance_response(attendance) for attendance in voucher.attendances
            ],
        )

    @staticmethod
    def _order_branch_id(items: Iterable[PurchaseOrderItem]) -> UUID:
        first = next(iter(items))
        return first.purchase_order.branch_id


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def fingerprint(data: AttendanceCreate) -> str:
    payload = data.model_dump(mode="json")
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _voucher_verification_status(voucher: Voucher) -> str:
    if not voucher.attendances:
        return "PENDING_VERIFICATION"
    for attendance in voucher.attendances:
        if not attendance.verifications:
            return "PENDING_VERIFICATION"
        latest = max(attendance.verifications, key=lambda item: item.reviewed_at)
        if latest.decision != VerificationDecision.VERIFIED.value:
            return "PENDING_VERIFICATION"
    return "VERIFIED"


def _item_status(authorized: Decimal, attended: Decimal, order_available: Decimal | None) -> str:
    if attended >= authorized:
        return BalanceStatus.COMPLETED.value
    if order_available is not None and order_available <= 0:
        return BalanceStatus.BLOCKED_BY_ORDER_BALANCE.value
    if attended <= 0:
        return BalanceStatus.PENDING.value
    return BalanceStatus.PARTIALLY_ATTENDED.value

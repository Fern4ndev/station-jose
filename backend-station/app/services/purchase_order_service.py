"""Purchase order use cases and derived line balances."""

from datetime import UTC, date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ResourceNotFoundError
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.schemas.catalog import BranchResponse, FuelTypeResponse
from app.schemas.purchase_order import (
    PaginationResponse,
    PurchaseOrderCreate,
    PurchaseOrderItemResponse,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.tables import FuelType, PurchaseOrder, PurchaseOrderItem


class InvalidFuelTypeError(AppError):
    status_code = 422
    code = "INVALID_FUEL_TYPE"


class OrderHasVouchersError(AppError):
    status_code = 409
    code = "ORDER_HAS_VOUCHERS"


class OrderLineReductionError(AppError):
    status_code = 409
    code = "ORDER_LINE_BELOW_ATTENDED"


class PurchaseOrderService:
    def __init__(self) -> None:
        self.orders = PurchaseOrderRepository()

    def create(self, db: Session, data: PurchaseOrderCreate) -> PurchaseOrderResponse:
        branch = self.orders.get_branch(db, data.branch_id)
        if branch is None or not branch.is_active:
            raise ResourceNotFoundError("La sede no existe o está inactiva.")
        fuel_types = self.orders.get_fuel_types(db, (item.fuel_type_id for item in data.items))
        self._validate_fuel_types(data, fuel_types)

        order = PurchaseOrder(
            id=uuid4(),
            order_number=data.order_number.strip(),
            siaf_number=data.siaf_number.strip(),
            issue_date=data.issue_date,
            institution_name=data.institution_name.strip(),
            supplier_name=data.supplier_name.strip(),
            supplier_details=data.supplier_details,
            executing_unit=data.executing_unit.strip(),
            executing_unit_ruc=data.executing_unit_ruc.strip(),
            branch_id=data.branch_id,
        )
        order.items = [
            PurchaseOrderItem(
                id=uuid4(),
                fuel_type_id=item.fuel_type_id,
                authorized_gallons=item.authorized_gallons,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
            )
            for item in data.items
        ]
        db.add(order)
        db.flush()
        return self._to_response(db, order)

    def get(self, db: Session, order_id: UUID) -> PurchaseOrderResponse:
        order = self._get_order(db, order_id)
        return self._to_response(db, order)

    def list(
        self,
        db: Session,
        *,
        page: int,
        page_size: int,
        search: str | None,
        branch_id: UUID | None,
        issue_date_from: date | None,
        issue_date_to: date | None,
        sort_by: str,
        sort_order: str,
    ) -> PurchaseOrderListResponse:
        orders, total = self.orders.list(
            db,
            search=search,
            branch_id=branch_id,
            issue_date_from=issue_date_from,
            issue_date_to=issue_date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return PurchaseOrderListResponse(
            items=[self._to_response(db, order) for order in orders],
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                pages=ceil(total / page_size) if total else 0,
            ),
        )

    def update(
        self, db: Session, order_id: UUID, data: PurchaseOrderUpdate
    ) -> PurchaseOrderResponse:
        order = self._get_order(db, order_id)
        has_vouchers = self.orders.has_vouchers(db, order.id)
        if data.items is not None and has_vouchers:
            self._validate_existing_lines(db, order, data)
        if data.branch_id is not None:
            branch = self.orders.get_branch(db, data.branch_id)
            if branch is None or not branch.is_active:
                raise ResourceNotFoundError("La sede no existe o está inactiva.")
            order.branch_id = data.branch_id
        for field in (
            "siaf_number",
            "issue_date",
            "institution_name",
            "supplier_name",
            "supplier_details",
            "executing_unit",
            "executing_unit_ruc",
        ):
            value = getattr(data, field)
            if value is not None:
                setattr(order, field, value.strip() if isinstance(value, str) else value)
        if data.items is not None:
            fuel_types = self.orders.get_fuel_types(db, (item.fuel_type_id for item in data.items))
            self._validate_fuel_types(data, fuel_types)
            if has_vouchers:
                self._update_existing_items(order, data)
            else:
                self._replace_items(db, order, data)
        db.flush()
        return self._to_response(db, order)

    def delete(self, db: Session, order_id: UUID) -> None:
        order = self._get_order(db, order_id)
        if self.orders.has_vouchers(db, order.id):
            raise OrderHasVouchersError("No se puede eliminar una orden que tiene vales asociados.")
        order.deleted_at = datetime.now(UTC)
        db.flush()

    def _get_order(self, db: Session, order_id: UUID) -> PurchaseOrder:
        order = self.orders.get_by_id(db, order_id)
        if order is None:
            raise ResourceNotFoundError("Orden de compra no encontrada.")
        return order

    def _validate_fuel_types(
        self,
        data: PurchaseOrderCreate | PurchaseOrderUpdate,
        fuel_types: dict[UUID, FuelType],
    ) -> None:
        requested_ids = {item.fuel_type_id for item in data.items or []}
        missing = requested_ids - fuel_types.keys()
        inactive = [fuel.code for fuel in fuel_types.values() if not fuel.is_active]
        if missing or inactive:
            raise InvalidFuelTypeError("Una o más líneas usan un combustible inválido o inactivo.")

    def _validate_existing_lines(
        self, db: Session, order: PurchaseOrder, data: PurchaseOrderUpdate
    ) -> None:
        attended = self.orders.attended_by_order_item_ids(db, (item.id for item in order.items))
        current_by_fuel = {item.fuel_type_id: item for item in order.items}
        requested_fuels = {item.fuel_type_id for item in data.items or []}
        if set(current_by_fuel) - requested_fuels:
            raise OrderHasVouchersError(
                "No se pueden eliminar líneas de una orden con vales asociados."
            )
        for item in data.items or []:
            current = current_by_fuel.get(item.fuel_type_id)
            if current is not None and item.authorized_gallons < attended.get(
                current.id, Decimal("0")
            ):
                raise OrderLineReductionError(
                    "No se puede reducir una línea por debajo de lo ya atendido."
                )

    def _replace_items(self, db: Session, order: PurchaseOrder, data: PurchaseOrderUpdate) -> None:
        for current in list(order.items):
            db.delete(current)
        order.items = []
        order.items.extend(
            PurchaseOrderItem(
                id=uuid4(),
                fuel_type_id=item.fuel_type_id,
                authorized_gallons=item.authorized_gallons,
                unit_price=item.unit_price,
                total_amount=item.total_amount,
            )
            for item in data.items or []
        )

    def _update_existing_items(self, order: PurchaseOrder, data: PurchaseOrderUpdate) -> None:
        current_by_fuel = {item.fuel_type_id: item for item in order.items}
        requested_fuels = {item.fuel_type_id for item in data.items or []}
        for item in data.items or []:
            current = current_by_fuel.get(item.fuel_type_id)
            if current is None:
                order.items.append(
                    PurchaseOrderItem(
                        id=uuid4(),
                        fuel_type_id=item.fuel_type_id,
                        authorized_gallons=item.authorized_gallons,
                        unit_price=item.unit_price,
                        total_amount=item.total_amount,
                    )
                )
                continue
            current.authorized_gallons = item.authorized_gallons
            current.unit_price = item.unit_price
            current.total_amount = item.total_amount
        for current in order.items:
            if current.fuel_type_id not in requested_fuels:
                raise OrderHasVouchersError(
                    "No se pueden eliminar líneas de una orden con vales asociados."
                )

    def _to_response(self, db: Session, order: PurchaseOrder) -> PurchaseOrderResponse:
        attended = self.orders.attended_by_order_item_ids(db, (item.id for item in order.items))
        item_responses: list[PurchaseOrderItemResponse] = []
        for item in order.items:
            consumed = attended.get(item.id, Decimal("0"))
            available = item.authorized_gallons - consumed
            item_responses.append(
                PurchaseOrderItemResponse(
                    id=item.id,
                    fuel_type=FuelTypeResponse.model_validate(item.fuel_type),
                    authorized_gallons=item.authorized_gallons,
                    attended_gallons=consumed,
                    available_gallons=available,
                    status="AVAILABLE" if available > 0 else "DEPLETED",
                    unit_price=item.unit_price,
                    total_amount=item.total_amount,
                )
            )
        return PurchaseOrderResponse(
            id=order.id,
            order_number=order.order_number,
            siaf_number=order.siaf_number,
            issue_date=order.issue_date,
            institution_name=order.institution_name,
            supplier_name=order.supplier_name,
            supplier_details=order.supplier_details,
            executing_unit=order.executing_unit,
            executing_unit_ruc=order.executing_unit_ruc,
            branch=BranchResponse.model_validate(order.branch),
            deleted_at=order.deleted_at,
            items=item_responses,
            status="AVAILABLE"
            if any(item.available_gallons > 0 for item in item_responses)
            else "DEPLETED",
        )

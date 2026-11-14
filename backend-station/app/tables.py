"""SQLAlchemy 2.x entities for the San José domain."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

UUIDType = PostgreSQLUUID(as_uuid=True)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("code"), UniqueConstraint("name"))

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="branch")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="branch")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="branch")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("dni"),
        UniqueConstraint("email"),
        CheckConstraint("role IN ('ADMIN', 'OFFICE', 'ATTENDANT')", name="ck_users_role"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    dni: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column(
        UUIDType, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    branch: Mapped[Branch | None] = relationship(back_populates="users")
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="performed_by")
    verifications: Mapped[list["AttendanceVerification"]] = relationship(back_populates="reviewed_by")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (UniqueConstraint("jti"), Index("ix_auth_sessions_user_expires", "user_id", "expires_at"))

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class FuelType(Base):
    __tablename__ = "fuel_types"
    __table_args__ = (UniqueConstraint("code"), UniqueConstraint("name"))

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    purchase_order_items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="fuel_type")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("executing_unit_ruc", "order_number", name="uq_purchase_order_identity"),
        Index("ix_purchase_orders_issue_date", "issue_date"),
        Index("ix_purchase_orders_institution_name", "institution_name"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(60), nullable=False)
    siaf_number: Mapped[str] = mapped_column(String(60), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    institution_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier_details: Mapped[str | None] = mapped_column(Text)
    executing_unit: Mapped[str] = mapped_column(String(200), nullable=False)
    executing_unit_ruc: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    branch: Mapped[Branch] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")
    vouchers: Mapped[list["Voucher"]] = relationship(back_populates="purchase_order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "fuel_type_id", name="uq_order_item_fuel"),
        UniqueConstraint("id", "purchase_order_id", name="uq_order_item_composite"),
        CheckConstraint("authorized_gallons > 0", name="ck_order_item_gallons_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_order_item_total_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    purchase_order_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False)
    fuel_type_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("fuel_types.id", ondelete="RESTRICT"), nullable=False)
    authorized_gallons: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    fuel_type: Mapped[FuelType] = relationship(back_populates="purchase_order_items")
    voucher_items: Mapped[list["VoucherItem"]] = relationship(back_populates="purchase_order_item")


class Voucher(Base):
    __tablename__ = "vouchers"
    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id", "issuer_type", "issuer_normalized", "voucher_number_normalized",
            name="uq_voucher_institution_identity",
        ),
        Index("ix_vouchers_number_normalized", "voucher_number_normalized"),
        CheckConstraint("issuer_type IN ('INSTITUTION', 'STATION')", name="ck_vouchers_issuer_type"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    purchase_order_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False)
    issuer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    voucher_number: Mapped[str] = mapped_column(String(60), nullable=False)
    voucher_number_normalized: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="vouchers")
    items: Mapped[list["VoucherItem"]] = relationship(back_populates="voucher")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="voucher")


class VoucherItem(Base):
    __tablename__ = "voucher_items"
    __table_args__ = (
        UniqueConstraint("voucher_id", "purchase_order_item_id", name="uq_voucher_item_order_item"),
        ForeignKeyConstraint(
            ["purchase_order_item_id", "purchase_order_id"],
            ["purchase_order_items.id", "purchase_order_items.purchase_order_id"],
            ondelete="RESTRICT",
            name="fk_voucher_item_order_item_same_order",
        ),
        CheckConstraint("authorized_gallons > 0", name="ck_voucher_item_gallons_positive"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    voucher_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("vouchers.id", ondelete="RESTRICT"), nullable=False)
    purchase_order_id: Mapped[UUID] = mapped_column(UUIDType, nullable=False)
    purchase_order_item_id: Mapped[UUID] = mapped_column(UUIDType, nullable=False)
    authorized_gallons: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    voucher: Mapped[Voucher] = relationship(back_populates="items")
    purchase_order_item: Mapped[PurchaseOrderItem] = relationship(back_populates="voucher_items")
    attendance_items: Mapped[list["AttendanceItem"]] = relationship(back_populates="voucher_item")


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("idempotency_key"), Index("ix_attendances_attended_at", "attended_at"))

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    voucher_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("vouchers.id", ondelete="RESTRICT"), nullable=False)
    performed_by_user_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    attended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(UUIDType, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    voucher: Mapped[Voucher] = relationship(back_populates="attendances")
    performed_by: Mapped[User] = relationship(back_populates="attendances")
    branch: Mapped[Branch] = relationship(back_populates="attendances")
    items: Mapped[list["AttendanceItem"]] = relationship(back_populates="attendance")
    verifications: Mapped[list["AttendanceVerification"]] = relationship(back_populates="attendance")


class AttendanceItem(Base):
    __tablename__ = "attendance_items"
    __table_args__ = (
        UniqueConstraint("attendance_id", "voucher_item_id", name="uq_attendance_item_voucher_item"),
        CheckConstraint("attended_gallons > 0", name="ck_attendance_item_gallons_positive"),
        CheckConstraint("unit_price_snapshot >= 0", name="ck_attendance_item_unit_price_nonnegative"),
        CheckConstraint("attended_amount >= 0", name="ck_attendance_item_amount_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    attendance_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("attendances.id", ondelete="RESTRICT"), nullable=False)
    voucher_item_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("voucher_items.id", ondelete="RESTRICT"), nullable=False)
    attended_gallons: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    attended_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    attendance: Mapped[Attendance] = relationship(back_populates="items")
    voucher_item: Mapped[VoucherItem] = relationship(back_populates="attendance_items")


class AttendanceVerification(Base):
    __tablename__ = "attendance_verifications"
    __table_args__ = (
        CheckConstraint("decision IN ('VERIFIED', 'OBSERVED')", name="ck_verification_decision"),
    )

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    attendance_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("attendances.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by_user_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    observation: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    attendance: Mapped[Attendance] = relationship(back_populates="verifications")
    reviewed_by: Mapped[User] = relationship(back_populates="verifications")


class DocumentCounter(Base):
    __tablename__ = "document_counters"
    __table_args__ = (UniqueConstraint("counter_code"), CheckConstraint("last_value >= 0", name="ck_counter_nonnegative"))

    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    counter_code: Mapped[str] = mapped_column(String(40), nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

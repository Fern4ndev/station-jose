import type { DecimalInput } from './purchase-order.model';
import type { VoucherAuthorizationItem, VoucherIssuerType } from './voucher.model';

export interface AttendanceItemCreate {
  readonly purchase_order_item_id?: string | null;
  readonly voucher_item_id?: string | null;
  readonly attended_gallons: DecimalInput;
}

/** Primera atención de una orden: crea el vale y descuenta del saldo. */
export interface FirstAttendanceCreate {
  readonly items: readonly AttendanceItemCreate[];
  readonly issuer_type: VoucherIssuerType;
  readonly issuer_name: string;
  readonly voucher_number: string;
  readonly voucher_items: readonly VoucherAuthorizationItem[];
}

export interface FollowUpAttendanceCreate {
  readonly items: readonly AttendanceItemCreate[];
}

export interface AttendanceItemResponse {
  readonly id: string;
  readonly voucher_item_id: string;
  readonly attended_gallons: string;
  readonly unit_price_snapshot: string;
  readonly attended_amount: string;
}

export interface AttendanceResponse {
  readonly id: string;
  readonly voucher_id: string;
  readonly performed_by_user_id: string;
  readonly branch_id: string;
  readonly attended_at: string;
  readonly idempotency_key: string;
  readonly items: readonly AttendanceItemResponse[];
}

export interface OperationalAttendanceItem {
  readonly id: string;
  readonly voucher_item_id: string;
  readonly attended_gallons: string;
}

export interface OperationalAttendance {
  readonly id: string;
  readonly voucher_id: string;
  readonly performed_by_user_id: string;
  readonly branch_id: string;
  readonly attended_at: string;
  readonly idempotency_key: string;
  readonly items: readonly OperationalAttendanceItem[];
}

export type AttendanceResult = AttendanceResponse | OperationalAttendance;

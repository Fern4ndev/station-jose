import type { AttendanceResponse, OperationalAttendance } from './attendance.model';
import type { DecimalInput } from './purchase-order.model';
import type { PaginatedResponse, Pagination } from './pagination.model';

export type VoucherIssuerType = 'INSTITUTION' | 'STATION';

/** Autorización por ítem que se declara al crear el primer vale. */
export interface VoucherAuthorizationItem {
  readonly purchase_order_item_id: string;
  readonly authorized_gallons: DecimalInput;
}

export interface VoucherDescriptiveUpdate {
  readonly issuer_type?: VoucherIssuerType | null;
  readonly issuer_name?: string | null;
  readonly voucher_number?: string | null;
}

export interface VoucherItemDetailResponse {
  readonly id: string;
  readonly purchase_order_item_id: string;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
}

export interface VoucherResponse {
  readonly id: string;
  readonly purchase_order_id: string;
  readonly issuer_type: string;
  readonly issuer_name: string;
  readonly voucher_number: string;
  readonly created_at: string;
  readonly status: string;
  readonly items: readonly VoucherItemDetailResponse[];
  readonly attendances: readonly AttendanceResponse[];
}

export interface OperationalVoucherItem {
  readonly id: string;
  readonly purchase_order_item_id: string;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
}

export interface OperationalVoucher {
  readonly id: string;
  readonly purchase_order_id: string;
  readonly issuer_type: string;
  readonly issuer_name: string;
  readonly voucher_number: string;
  readonly created_at: string;
  readonly status: string;
  readonly items: readonly OperationalVoucherItem[];
  readonly attendances: readonly OperationalAttendance[];
}

export type VoucherDetail = VoucherResponse | OperationalVoucher;
export type VoucherListResponse = PaginatedResponse<VoucherResponse>;

export interface OperationalVoucherList {
  readonly items: readonly OperationalVoucher[];
  readonly pagination: Pagination;
}

export interface VoucherQuery {
  readonly page?: number;
  readonly page_size?: number;
  readonly purchase_order_id?: string | null;
  readonly voucher_number?: string | null;
  readonly issuer_name?: string | null;
  readonly created_from?: string | null;
  readonly created_to?: string | null;
}

export interface AttendedVoucherQuery {
  readonly page?: number;
  readonly page_size?: number;
  readonly voucher_number?: string | null;
}

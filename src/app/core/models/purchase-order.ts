import type { BranchResponse, FuelTypeResponse } from './catalog';
import type { PaginatedResponse, Pagination } from './pagination';

/** FastAPI acepta `number` o `string` decimal en las entradas. */
export type DecimalInput = number | string;

export type OrderSortField = 'issue_date' | 'order_number' | 'institution_name';
export type SortOrder = 'asc' | 'desc';

/** Ordenamientos que acepta `GET /purchase-orders`. */
export const ORDER_SORT_FIELDS = [
  'issue_date',
  'order_number',
  'institution_name',
] as const satisfies readonly OrderSortField[];

export interface PurchaseOrderItemCreate {
  readonly fuel_type_id: string;
  readonly authorized_gallons: DecimalInput;
  readonly unit_price: DecimalInput;
  readonly total_amount: DecimalInput;
}

export interface PurchaseOrderCreate {
  readonly order_number: string;
  readonly siaf_number: string;
  readonly issue_date: string;
  readonly institution_name: string;
  readonly supplier_name: string;
  readonly supplier_details?: string | null;
  readonly executing_unit: string;
  readonly executing_unit_ruc: string;
  readonly branch_id: string;
  readonly items: readonly PurchaseOrderItemCreate[];
}

export interface PurchaseOrderUpdate {
  readonly siaf_number?: string | null;
  readonly issue_date?: string | null;
  readonly institution_name?: string | null;
  readonly supplier_name?: string | null;
  readonly supplier_details?: string | null;
  readonly executing_unit?: string | null;
  readonly executing_unit_ruc?: string | null;
  readonly branch_id?: string | null;
  readonly items?: readonly PurchaseOrderItemCreate[] | null;
}

export interface PurchaseOrderItemResponse {
  readonly id: string;
  readonly fuel_type: FuelTypeResponse;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
  readonly unit_price: string;
  readonly total_amount: string;
}

export interface PurchaseOrderResponse {
  readonly id: string;
  readonly order_number: string;
  readonly siaf_number: string;
  readonly issue_date: string;
  readonly institution_name: string;
  readonly supplier_name: string;
  readonly supplier_details: string | null;
  readonly executing_unit: string;
  readonly executing_unit_ruc: string;
  readonly branch: BranchResponse;
  readonly deleted_at: string | null;
  readonly items: readonly PurchaseOrderItemResponse[];
  readonly status: string;
}

/** Variante reducida para el rol ATTENDANT (sin precios). */
export interface OperationalOrderItem {
  readonly id: string;
  readonly fuel_type: FuelTypeResponse;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
}

export interface OperationalOrder {
  readonly id: string;
  readonly order_number: string;
  readonly siaf_number: string;
  readonly issue_date: string;
  readonly institution_name: string;
  readonly supplier_name: string;
  readonly supplier_details: string | null;
  readonly executing_unit: string;
  readonly executing_unit_ruc: string;
  readonly branch: BranchResponse;
  readonly deleted_at: string | null;
  readonly items: readonly OperationalOrderItem[];
  readonly status: string;
}

export type PurchaseOrderDetail = PurchaseOrderResponse | OperationalOrder;
export type PurchaseOrderListResponse = PaginatedResponse<PurchaseOrderResponse>;

export interface OperationalOrderList {
  readonly items: readonly OperationalOrder[];
  readonly pagination: Pagination;
}

export type PurchaseOrderQuery = {
  readonly search?: string | null;
  readonly branch_id?: string | null;
  readonly issue_date_from?: string | null;
  readonly issue_date_to?: string | null;
  readonly page?: number;
  readonly page_size?: number;
  readonly sort_by?: OrderSortField;
  readonly sort_order?: SortOrder;
};

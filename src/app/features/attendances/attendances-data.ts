import type { DecimalInput } from '../../core/models/purchase-order';
import type { VoucherIssuerType } from '../vouchers/vouchers-data';

export type AttendanceStatus = 'Confirmada';

export interface AttendanceFuelLine {
  readonly id: string;
  readonly fuel: string;
  readonly gallons: number;
  readonly authorized?: number;
}

export interface DemoAttendance {
  readonly id: string;
  readonly voucher: string;
  readonly orderId: string;
  readonly attendant: string;
  readonly branch: string;
  readonly gallons: number;
  readonly fuel?: string;
  readonly issuer?: string;
  readonly institution?: string;
  /** Galones autorizados en la línea del vale, si está disponible. */
  readonly authorized?: number;
  /** Combustibles entregados en una misma atención. */
  readonly lines?: readonly AttendanceFuelLine[];
  readonly time: string;
  readonly date: string;
  readonly status: AttendanceStatus;
  readonly attendedAt?: string;
}

/** Una línea de combustible dentro de la atención. */
export interface AttendanceLineRequest {
  /** Línea de la orden (`purchase_order_items.id`). */
  readonly orderItemId: string;
  /** Línea del vale cuando la atención es posterior; ausente en un vale nuevo. */
  readonly voucherItemId?: string;
  /** Galones autorizados; solo se envían al crear el vale. */
  readonly authorized: DecimalInput;
  /** Galones realmente entregados, normalizados a 3 decimales. */
  readonly gallons: DecimalInput;
}

export interface AttendanceRequest {
  /** Orden de compra (`purchase_orders.id`). */
  readonly purchaseOrderId: string;
  readonly voucherId: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
  readonly branch: string;
  readonly lines: readonly AttendanceLineRequest[];
}

export function visibleAttendances(
  items: readonly DemoAttendance[],
  attendant: string | null,
  branch: string,
): readonly DemoAttendance[] {
  return items.filter(
    (item) =>
      (branch === 'Todas las sedes' || item.branch === branch) &&
      (attendant === null || item.attendant === attendant),
  );
}

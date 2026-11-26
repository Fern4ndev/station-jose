import type { DecimalInput } from '../../core/models/purchase-order';
import type { VoucherIssuerType } from '../vouchers/vouchers-data';

export type AttendanceStatus = 'Confirmada';

export interface DemoAttendance {
  readonly id: string;
  readonly voucher: string;
  readonly orderId: string;
  readonly attendant: string;
  readonly branch: string;
  readonly gallons: number;
  readonly time: string;
  readonly date: string;
  readonly status: AttendanceStatus;
  readonly attendedAt?: string;
}

export interface AttendanceRequest {
  readonly orderId: string;
  readonly voucherId: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
  readonly authorized: DecimalInput;
  /** Se envía como string decimal normalizado (3 decimales). */
  readonly gallons: DecimalInput;
  readonly branch: string;
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

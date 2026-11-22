import { orderBalance, type DemoOrder } from '../orders/orders-data';
import {
  voucherBalance,
  type DemoVoucher,
  type VoucherIssuerType,
} from '../vouchers/vouchers-data';

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
}

export interface AttendanceRequest {
  readonly orderId: string;
  readonly voucherId: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
  readonly authorized: number;
  readonly gallons: number;
  readonly branch: string;
}

export interface AttendanceSnapshot {
  readonly attendances: readonly DemoAttendance[];
  readonly orders: readonly DemoOrder[];
  readonly vouchers: readonly DemoVoucher[];
}

export type AttendanceResult =
  | (AttendanceSnapshot & { readonly ok: true; readonly gallons: number })
  | { readonly ok: false; readonly message: string };

export const DEMO_ATTENDANCES: readonly DemoAttendance[] = [
  { id: 'a1', voucher: 'VM-2026-0142', orderId: 'OC-2026-0048', attendant: 'Luis Cárdenas', branch: 'San José', gallons: 35, time: '10:42', date: '15 nov 2026', status: 'Confirmada' },
  { id: 'a2', voucher: 'VM-2026-0141', orderId: 'OC-2026-0046', attendant: 'Rosa Méndez', branch: 'Santa Marta', gallons: 40, time: '10:16', date: '15 nov 2026', status: 'Confirmada' },
  { id: 'a3', voucher: 'VM-2026-0139', orderId: 'OC-2026-0044', attendant: 'Luis Cárdenas', branch: 'San José', gallons: 55, time: '09:58', date: '15 nov 2026', status: 'Confirmada' },
  { id: 'a4', voucher: 'VM-2026-0135', orderId: 'OC-2026-0035', attendant: 'Jorge Silva', branch: 'Santa Marta', gallons: 40, time: '09:31', date: '15 nov 2026', status: 'Confirmada' },
  { id: 'a5', voucher: 'VM-2026-0137', orderId: 'OC-2026-0038', attendant: 'Luis Cárdenas', branch: 'San José', gallons: 30, time: '08:57', date: '15 nov 2026', status: 'Confirmada' },
];

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

/**
 * Registra un despacho validando el saldo de la orden y del vale, igual que el
 * flujo del mockup: primera atención crea el vale, las siguientes consumen su
 * saldo sin tocar el historial.
 */
export function registerAttendance(
  snapshot: AttendanceSnapshot,
  request: AttendanceRequest,
  attendant: string,
): AttendanceResult {
  const order = snapshot.orders.find((item) => item.id === request.orderId);
  const voucherId = request.voucherId.trim();
  const gallons = request.gallons;

  if (!order || !voucherId || !Number.isFinite(gallons) || gallons <= 0 || gallons > orderBalance(order)) {
    return { ok: false, message: 'La cantidad supera el saldo disponible de la orden.' };
  }

  const existing = snapshot.vouchers.find(
    (voucher) => voucher.id.toLowerCase() === voucherId.toLowerCase(),
  );

  if (existing && (existing.orderId !== order.id || gallons > voucherBalance(existing))) {
    return {
      ok: false,
      message: 'El vale no corresponde a esta orden o no tiene saldo suficiente.',
    };
  }

  if (!existing && (request.authorized < gallons || request.authorized > orderBalance(order))) {
    return {
      ok: false,
      message: 'El saldo autorizado del vale debe cubrir el despacho y no superar el saldo de la orden.',
    };
  }

  const now = new Date();
  const voucher: DemoVoucher =
    existing ?? {
      id: voucherId,
      orderId: order.id,
      issuer: request.issuer.trim(),
      issuerType: request.issuerType,
      fuel: order.fuel,
      total: request.authorized,
      used: 0,
    };

  const vouchers = existing
    ? snapshot.vouchers.map((item) =>
        item.id === voucher.id ? { ...item, used: item.used + gallons } : item,
      )
    : [{ ...voucher, used: gallons }, ...snapshot.vouchers];

  const orders = snapshot.orders.map((item) =>
    item.id === order.id ? { ...item, used: item.used + gallons } : item,
  );

  const attendance: DemoAttendance = {
    id: `a${now.getTime()}`,
    voucher: voucher.id,
    orderId: order.id,
    attendant,
    branch: request.branch,
    gallons,
    time: now.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' }),
    date: now
      .toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
      .replace(/\./g, ''),
    status: 'Confirmada',
  };

  return {
    ok: true,
    gallons,
    attendances: [attendance, ...snapshot.attendances],
    orders,
    vouchers,
  };
}

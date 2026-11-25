import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { PurchaseOrderDetail } from '../../core/models/purchase-order';
import type { AttendanceResult } from '../../core/models/attendance';
import type { VoucherDetail } from '../../core/models/voucher';
import { AttendancesApi } from '../../core/services/attendances-api';
import { AuthService } from '../../core/services/auth/auth';
import { PurchaseOrdersApi } from '../../core/services/purchase-orders-api';
import { VouchersApi } from '../../core/services/vouchers-api';
import type { DemoOrder } from '../orders/orders-data';
import type { DemoVoucher } from '../vouchers/vouchers-data';
import type { AttendanceRequest, DemoAttendance } from './attendances-data';

export interface DispatchOrder extends DemoOrder {
  readonly apiId: string;
  readonly orderNumber: string;
  readonly institutionRuc: string;
}

export interface DispatchVoucher extends DemoVoucher {
  readonly apiId: string;
  readonly itemId: string;
  readonly orderItemId: string;
  readonly branch: string;
}

/** Datos operativos leídos del servidor; sobreviven al cambio de ruta. */
@Injectable({ providedIn: 'root' })
export class OperationsStore {
  private readonly pendingDispatches = new Map<string, string>();
  private readonly ordersApi = inject(PurchaseOrdersApi);
  private readonly vouchersApi = inject(VouchersApi);
  private readonly attendancesApi = inject(AttendancesApi);
  private readonly auth = inject(AuthService);

  private readonly ordersState = signal<readonly DispatchOrder[]>([]);
  private readonly vouchersState = signal<readonly DispatchVoucher[]>([]);
  private readonly attendancesState = signal<readonly DemoAttendance[]>([]);

  readonly orders = this.ordersState.asReadonly();
  readonly vouchers = this.vouchersState.asReadonly();
  readonly attendances = this.attendancesState.asReadonly();

  async load(): Promise<void> {
    const [orderDetails, voucherDetails, attendanceDetails] = await Promise.all([
      this.loadOrders(), this.loadVouchers(), this.loadAttendances(),
    ]);
    const orders: DispatchOrder[] = orderDetails.flatMap((order) =>
      order.items.map((item) => ({
        id: item.id,
        apiId: order.id,
        orderNumber: order.order_number,
        institutionRuc: order.executing_unit_ruc.trim(),
        entity: order.institution_name,
        date: order.issue_date,
        branch: order.branch.name,
        fuel: item.fuel_type.name,
        note: order.supplier_details?.trim() ?? '',
        total: Number(item.authorized_gallons),
        used: Number(item.attended_gallons),
      })),
    );
    const orderById = new Map(orderDetails.map((order) => [order.id, order]));
    const orderItemById = new Map(orders.map((order) => [order.id, order]));
    const vouchers: DispatchVoucher[] = voucherDetails.flatMap((voucher) => {
      const order = orderById.get(voucher.purchase_order_id);
      return voucher.items.map((item) => ({
        id: voucher.voucher_number,
        apiId: voucher.id,
        itemId: item.id,
        orderItemId: item.purchase_order_item_id,
        orderId: order?.order_number ?? voucher.purchase_order_id,
        issuer: voucher.issuer_name,
        issuerType: voucher.issuer_type as DispatchVoucher['issuerType'],
        fuel: orderItemById.get(item.purchase_order_item_id)?.fuel ?? 'Combustible',
        branch: order?.branch.name ?? '',
        backendStatus: voucher.status,
        lines: voucher.items.map((line) => ({
          id: line.id,
          fuel: orderItemById.get(line.purchase_order_item_id)?.fuel ?? 'Combustible',
          authorized: Number(line.authorized_gallons),
          attended: Number(line.attended_gallons),
          available: Number(line.available_gallons),
          status: line.status,
        })),
        total: Number(item.authorized_gallons),
        used: Number(item.attended_gallons),
      }));
    });
    const voucherById = new Map(voucherDetails.map((voucher) => [voucher.id, voucher]));
    const attendances: DemoAttendance[] = attendanceDetails.flatMap((attendance) => {
      const voucher = voucherById.get(attendance.voucher_id);
      if (!voucher) return [];
      const order = orderById.get(voucher.purchase_order_id);
      return attendance.items.map((item) => ({
          id: `${attendance.id}:${item.id}`,
          voucher: voucher.voucher_number,
          orderId: order?.order_number ?? voucher.purchase_order_id,
          attendant: attendance.performer_name ?? (attendance.performed_by_user_id === this.auth.currentUser()?.id
            ? this.auth.fullName()
            : attendance.performed_by_user_id.slice(0, 8)),
          branch: attendance.branch_name ?? order?.branch.name ?? '',
          gallons: Number(item.attended_gallons),
          time: new Date(attendance.attended_at).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Lima' }),
          date: new Date(attendance.attended_at).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'America/Lima' }).replace(/\./g, ''),
          attendedAt: attendance.attended_at,
          status: 'Confirmada' as const,
        }));
    }).sort((a, b) => (b.attendedAt ?? '').localeCompare(a.attendedAt ?? ''));
    this.ordersState.set(orders);
    this.vouchersState.set(vouchers);
    this.attendancesState.set(attendances);
  }

  async register(request: AttendanceRequest): Promise<void> {
    const serialized = JSON.stringify({ user_id: this.auth.currentUser()?.id, request });
    if (!this.pendingDispatches.has(serialized)) {
      this.pendingDispatches.set(serialized, this.readPendingKey(serialized) ?? crypto.randomUUID());
    }
    const idempotencyKey = this.pendingDispatches.get(serialized)!;
    this.writePendingKey(serialized, idempotencyKey);
    const order = this.ordersState().find((item) => item.id === request.orderId);
    if (!order) throw new Error('Selecciona una orden disponible del servidor.');
    const normalize = (value: string) => value.normalize('NFKC').trim().toLocaleLowerCase().replace(/\s+/g, ' ');
    const voucher = this.vouchersState().find((item) =>
      item.orderItemId === order.id
      && normalize(item.id) === normalize(request.voucherId)
      && normalize(item.issuer) === normalize(request.issuer),
    );
    if (voucher) {
      await firstValueFrom(this.attendancesApi.createFollowUp(voucher.apiId, {
        items: [{ voucher_item_id: voucher.itemId, attended_gallons: request.gallons }],
      }, idempotencyKey));
    } else {
      await firstValueFrom(this.attendancesApi.createFirst(order.apiId, {
        issuer_type: request.issuerType,
        issuer_name: request.issuer,
        voucher_number: request.voucherId,
        voucher_items: [{ purchase_order_item_id: order.id, authorized_gallons: request.authorized }],
        items: [{ purchase_order_item_id: order.id, attended_gallons: request.gallons }],
      }, idempotencyKey));
    }
    await this.load();
    this.pendingDispatches.delete(serialized);
    this.removePendingKey(serialized);
  }

  private storageKey(serialized: string): string {
    return `san-jose:attendance-pending:${serialized}`;
  }

  private readPendingKey(serialized: string): string | null {
    try { return sessionStorage.getItem(this.storageKey(serialized)); }
    catch { return null; }
  }

  private writePendingKey(serialized: string, key: string): void {
    try { sessionStorage.setItem(this.storageKey(serialized), key); }
    catch { /* El reintento dentro de esta sesión conserva la clave en memoria. */ }
  }

  private removePendingKey(serialized: string): void {
    try { sessionStorage.removeItem(this.storageKey(serialized)); }
    catch { /* El despacho ya fue confirmado y la memoria quedó limpia. */ }
  }

  private async loadOrders(): Promise<PurchaseOrderDetail[]> {
    const items: PurchaseOrderDetail[] = [];
    for (let page = 1; ; page += 1) {
      const result = await firstValueFrom(this.ordersApi.list({ page, page_size: 100 }));
      items.push(...result.items);
      if (page >= result.pagination.pages) return items;
    }
  }

  private async loadVouchers(): Promise<VoucherDetail[]> {
    const items: VoucherDetail[] = [];
    for (let page = 1; ; page += 1) {
      const result = await firstValueFrom(this.vouchersApi.list({ page, page_size: 100 }));
      items.push(...result.items);
      if (page >= result.pagination.pages) return items;
    }
  }

  private async loadAttendances(): Promise<AttendanceResult[]> {
    const items: AttendanceResult[] = [];
    for (let page = 1; ; page += 1) {
      const result = await firstValueFrom(this.attendancesApi.list({ page, page_size: 100 }));
      items.push(...result.items);
      if (page >= result.pagination.pages) return items;
    }
  }
}

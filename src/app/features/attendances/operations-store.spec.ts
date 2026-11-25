import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';
import { AttendancesApi } from '../../core/services/attendances-api';
import { AuthService } from '../../core/services/auth/auth';
import { PurchaseOrdersApi } from '../../core/services/purchase-orders-api';
import { VouchersApi } from '../../core/services/vouchers-api';
import { OperationsStore } from './operations-store';

const pagination = { page: 1, page_size: 100, total: 1, pages: 1 };
const order = {
  id: 'order-uuid', order_number: 'OC-01', institution_name: 'Municipalidad', executing_unit_ruc: '20123456789',
  issue_date: '2026-11-23', branch: { id: 'branch-uuid', code: 'SAN_JOSE', name: 'San José', is_active: true },
  items: [{ id: 'order-item-uuid', fuel_type: { id: 'fuel-uuid', code: 'DIESEL', name: 'Diésel', is_active: true }, authorized_gallons: '100', attended_gallons: '0', available_gallons: '100' }],
};
const voucher = {
  id: 'voucher-uuid', purchase_order_id: 'order-uuid', issuer_type: 'INSTITUTION',
  issuer_name: 'Municipalidad', voucher_number: 'VM-01', created_at: '2026-11-23T10:00:00Z', status: 'PARTIALLY_ATTENDED',
  items: [{ id: 'voucher-item-uuid', purchase_order_item_id: 'order-item-uuid', authorized_gallons: '50', attended_gallons: '20', available_gallons: '30', status: 'PARTIALLY_ATTENDED' }],
  attendances: [{ id: 'attendance-uuid', voucher_id: 'voucher-uuid', performed_by_user_id: 'user-uuid', branch_id: 'branch-uuid', attended_at: '2026-11-23T10:00:00Z', idempotency_key: 'key-uuid', items: [{ id: 'attendance-item-uuid', voucher_item_id: 'voucher-item-uuid', attended_gallons: '20' }] }],
};

describe('OperationsStore', () => {
  it('reutiliza la clave de idempotencia al reintentar el mismo despacho', async () => {
    const ordersApi = { list: vi.fn().mockReturnValue(of({ items: [order], pagination })) };
    const vouchersApi = { list: vi.fn().mockReturnValue(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } })) };
    const attendancesApi = {
      list: vi.fn().mockReturnValue(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } })),
      createFirst: vi.fn()
        .mockReturnValueOnce(throwError(() => new Error('Red interrumpida')))
        .mockReturnValueOnce(of({ id: 'attendance-uuid' })),
      createFollowUp: vi.fn(),
    };
    TestBed.configureTestingModule({ providers: [
      OperationsStore,
      { provide: PurchaseOrdersApi, useValue: ordersApi },
      { provide: VouchersApi, useValue: vouchersApi },
      { provide: AttendancesApi, useValue: attendancesApi },
      { provide: AuthService, useValue: { currentUser: () => ({ id: 'user-uuid' }), fullName: () => 'Grifero Uno' } },
    ] });
    const store = TestBed.inject(OperationsStore);
    await store.load();
    expect(store.orders()[0].institutionRuc).toBe('20123456789');
    const request = { orderId: 'order-item-uuid', voucherId: 'VM-01', issuer: 'Municipalidad', issuerType: 'INSTITUTION' as const, authorized: 50, gallons: 20, branch: 'San José' };
    await expect(store.register(request)).rejects.toThrow('Red interrumpida');
    await store.register(request);
    expect(attendancesApi.createFirst.mock.calls[0][2]).toBe(attendancesApi.createFirst.mock.calls[1][2]);
  });

  it('guarda la primera atención en la API y la recupera al recargar', async () => {
    const ordersApi = { list: vi.fn().mockReturnValue(of({ items: [order], pagination })) };
    const vouchersApi = { list: vi.fn()
      .mockReturnValueOnce(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } }))
      .mockReturnValueOnce(of({ items: [voucher], pagination })) };
    const attendancesApi = {
      list: vi.fn()
        .mockReturnValueOnce(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } }))
        .mockReturnValueOnce(of({ items: voucher.attendances, pagination })),
      createFirst: vi.fn().mockReturnValue(of({ id: 'attendance-uuid' })), createFollowUp: vi.fn(),
    };
    TestBed.configureTestingModule({ providers: [
      OperationsStore,
      { provide: PurchaseOrdersApi, useValue: ordersApi },
      { provide: VouchersApi, useValue: vouchersApi },
      { provide: AttendancesApi, useValue: attendancesApi },
      { provide: AuthService, useValue: { currentUser: () => ({ id: 'user-uuid' }), fullName: () => 'Grifero Uno' } },
    ] });
    const store = TestBed.inject(OperationsStore);
    await store.load();
    expect(store.attendances()).toHaveLength(0);

    await store.register({ orderId: 'order-item-uuid', voucherId: 'VM-01', issuer: 'Municipalidad', issuerType: 'INSTITUTION', authorized: 50, gallons: 20, branch: 'San José' });

    expect(attendancesApi.createFirst).toHaveBeenCalledWith('order-uuid', expect.objectContaining({
      voucher_number: 'VM-01',
      items: [{ purchase_order_item_id: 'order-item-uuid', attended_gallons: 20 }],
    }), expect.any(String));
    expect(store.vouchers()[0].id).toBe('VM-01');
    expect(store.attendances()[0].gallons).toBe(20);
  });

  it('envía una atención posterior usando la línea del vale persistido', async () => {
    const ordersApi = { list: vi.fn().mockReturnValue(of({ items: [order], pagination })) };
    const vouchersApi = { list: vi.fn().mockReturnValue(of({ items: [voucher], pagination })) };
    const attendancesApi = { list: vi.fn().mockReturnValue(of({ items: voucher.attendances, pagination })), createFirst: vi.fn(), createFollowUp: vi.fn().mockReturnValue(of({ id: 'next-attendance' })) };
    TestBed.configureTestingModule({ providers: [
      OperationsStore,
      { provide: PurchaseOrdersApi, useValue: ordersApi },
      { provide: VouchersApi, useValue: vouchersApi },
      { provide: AttendancesApi, useValue: attendancesApi },
      { provide: AuthService, useValue: { currentUser: () => ({ id: 'user-uuid' }), fullName: () => 'Grifero Uno' } },
    ] });
    const store = TestBed.inject(OperationsStore);
    await store.load();

    await store.register({ orderId: 'order-item-uuid', voucherId: 'VM-01', issuer: 'Municipalidad', issuerType: 'INSTITUTION', authorized: 50, gallons: 10, branch: 'San José' });

    expect(attendancesApi.createFollowUp).toHaveBeenCalledWith('voucher-uuid', {
      items: [{ voucher_item_id: 'voucher-item-uuid', attended_gallons: 10 }],
    }, expect.any(String));
    expect(attendancesApi.createFirst).not.toHaveBeenCalled();
  });
});

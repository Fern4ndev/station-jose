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
  it('muestra una fila por atención con todos sus combustibles y mantiene separados los despachos del mismo vale', async () => {
    const secondOrderItem = { ...order.items[0], id: 'order-item-2', fuel_type: { ...order.items[0].fuel_type, name: 'Gasolina' } };
    const multiOrder = { ...order, items: [...order.items, secondOrderItem] };
    const multiVoucher = { ...voucher, items: [...voucher.items, { ...voucher.items[0], id: 'voucher-item-2', purchase_order_item_id: 'order-item-2' }] };
    const first = { ...voucher.attendances[0], items: [
      { ...voucher.attendances[0].items[0], attended_gallons: '10.125' },
      { id: 'attendance-item-2', voucher_item_id: 'voucher-item-2', attended_gallons: '4.875' },
    ] };
    const second = { ...first, id: 'next-attendance', attended_at: '2026-11-24T10:00:00Z', items: [
      { ...first.items[0], id: 'next-item-1', attended_gallons: '0.100' },
      { ...first.items[1], id: 'next-item-2', attended_gallons: '0.200' },
    ] };
    TestBed.configureTestingModule({ providers: [
      OperationsStore,
      { provide: PurchaseOrdersApi, useValue: { list: () => of({ items: [multiOrder], pagination }) } },
      { provide: VouchersApi, useValue: { list: () => of({ items: [multiVoucher], pagination }) } },
      { provide: AttendancesApi, useValue: { list: () => of({ items: [first, second], pagination }) } },
      { provide: AuthService, useValue: { currentUser: () => ({ id: 'user-uuid' }), fullName: () => 'Grifero Uno' } },
    ] });
    const store = TestBed.inject(OperationsStore);
    await store.load();
    expect(store.attendances()).toHaveLength(2);
    expect(store.attendances()[0]).toEqual(expect.objectContaining({
      id: 'next-attendance', gallons: 0.3,
      lines: [expect.objectContaining({ fuel: 'Diésel', gallons: 0.1 }), expect.objectContaining({ fuel: 'Gasolina', gallons: 0.2 })],
    }));
    expect(store.attendances()[1]).toEqual(expect.objectContaining({ id: 'attendance-uuid', gallons: 15 }));
    await store.load();
    expect(store.attendances()).toHaveLength(2);
  });

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
    const request = {
      purchaseOrderId: 'order-uuid',
      voucherId: 'VM-01',
      issuer: 'Municipalidad',
      issuerType: 'INSTITUTION' as const,
      branch: 'San José',
      lines: [{ orderItemId: 'order-item-uuid', authorized: '50.000', gallons: '20.000' }],
    };
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

    await store.register({
      purchaseOrderId: 'order-uuid',
      voucherId: 'VM-01',
      issuer: 'Municipalidad',
      issuerType: 'INSTITUTION',
      branch: 'San José',
      lines: [{ orderItemId: 'order-item-uuid', authorized: '50.000', gallons: '20.000' }],
    });

    expect(attendancesApi.createFirst).toHaveBeenCalledWith('order-uuid', expect.objectContaining({
      voucher_number: 'VM-01',
      voucher_items: [{ purchase_order_item_id: 'order-item-uuid', authorized_gallons: '50.000' }],
      items: [{ purchase_order_item_id: 'order-item-uuid', attended_gallons: '20.000' }],
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

    await store.register({
      purchaseOrderId: 'order-uuid',
      voucherId: 'VM-01',
      issuer: 'Municipalidad',
      issuerType: 'INSTITUTION',
      branch: 'San José',
      lines: [{
        orderItemId: 'order-item-uuid',
        voucherItemId: 'voucher-item-uuid',
        authorized: '50.000',
        gallons: '10.000',
      }],
    });

    expect(attendancesApi.createFollowUp).toHaveBeenCalledWith('voucher-uuid', {
      items: [{ voucher_item_id: 'voucher-item-uuid', attended_gallons: '10.000' }],
    }, expect.any(String));
    expect(attendancesApi.createFirst).not.toHaveBeenCalled();
  });

  it('crea un vale con varios combustibles en una sola atención', async () => {
    const multiOrder = {
      ...order,
      items: [
        order.items[0],
        { id: 'order-item-2', fuel_type: { id: 'fuel-2', code: 'GASOLINE', name: 'Gasolina', is_active: true }, authorized_gallons: '80', attended_gallons: '0', available_gallons: '80' },
      ],
    };
    const ordersApi = { list: vi.fn().mockReturnValue(of({ items: [multiOrder], pagination })) };
    const vouchersApi = { list: vi.fn().mockReturnValue(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } })) };
    const attendancesApi = {
      list: vi.fn().mockReturnValue(of({ items: [], pagination: { ...pagination, total: 0, pages: 0 } })),
      createFirst: vi.fn().mockReturnValue(of({ id: 'attendance-uuid' })),
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

    await store.register({
      purchaseOrderId: 'order-uuid',
      voucherId: 'VM-02',
      issuer: 'Municipalidad',
      issuerType: 'INSTITUTION',
      branch: 'San José',
      lines: [
        { orderItemId: 'order-item-uuid', authorized: '50.000', gallons: '10.500' },
        { orderItemId: 'order-item-2', authorized: '80.000', gallons: '0.000' },
      ],
    });

    expect(attendancesApi.createFirst).toHaveBeenCalledWith('order-uuid', expect.objectContaining({
      voucher_items: [
        { purchase_order_item_id: 'order-item-uuid', authorized_gallons: '50.000' },
        { purchase_order_item_id: 'order-item-2', authorized_gallons: '80.000' },
      ],
      items: [{ purchase_order_item_id: 'order-item-uuid', attended_gallons: '10.500' }],
    }), expect.any(String));
  });
});

import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CatalogApi } from '../../core/services/catalog-api';
import { ReportsApi } from '../../core/services/reports-api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { Reports } from './reports';

async function setup() {
  const api = {
    dashboard: vi.fn(() => of({ orders: 0, vouchers: 0, attendances: 0, authorized_gallons: '0', attended_gallons: '0', available_gallons: '0', by_period: [] })),
    purchaseOrders: vi.fn(() => of({ items: [] })), attendances: vi.fn(() => of({ items: [] })),
    exportPurchaseOrders: vi.fn(() => of(new Blob(['report']))),
    exportAttendances: vi.fn(() => of(new Blob(['report']))),
  };
  const branch = signal('Todas las sedes');
  const messages = { add: vi.fn() };
  TestBed.configureTestingModule({ providers: [
    { provide: ReportsApi, useValue: api },
    { provide: CatalogApi, useValue: { branches: () => of([{ id: 'san-jose', name: 'San José' }]) } },
    { provide: AdminUiState, useValue: { branch } }, { provide: MessageService, useValue: messages },
  ] });
  TestBed.overrideComponent(Reports, { set: { template: '', imports: [] } });
  const fixture = TestBed.createComponent(Reports);
  fixture.detectChanges();
  await fixture.whenStable();
  await vi.waitFor(() => expect(fixture.componentInstance['refreshing']()).toBe(false));
  return { fixture, component: fixture.componentInstance, api, branch, messages };
}

describe('Report filter application', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('does not request or change visible data until Apply is pressed', async () => {
    const { component, api, fixture, branch } = await setup();
    const original = component['applied']();
    component['onView']('day');
    component['kind'].set('attendances');
    component['onHourFrom'](8);
    branch.set('San José');
    fixture.detectChanges();
    await fixture.whenStable();
    expect(api.dashboard).toHaveBeenCalledTimes(1);
    expect(component['applied']()).toBe(original);
    expect(component['activeKind']()).toBe('orders');
    expect(component['hasPending']()).toBe(true);

    await component['applyFilters']();
    expect(api.dashboard).toHaveBeenCalledTimes(2);
    expect(api.dashboard).toHaveBeenLastCalledWith(expect.objectContaining({ group_by: 'hour', hour_from: 8, branch_id: 'san-jose' }));
    expect(component['activeKind']()).toBe('attendances');
    expect(component['visibleBuckets']()).toHaveLength(24);
    expect(component['hasPending']()).toBe(false);
  });

  it('refreshes the applied selection while draft filters are pending', async () => {
    const { component, api } = await setup();
    const original = component['applied']();
    component['onView']('year');
    await component['refresh']();
    expect(api.dashboard).toHaveBeenCalledTimes(2);
    expect(api.dashboard).toHaveBeenLastCalledWith(expect.objectContaining({ group_by: 'day', date_from: original.from, date_to: original.to }));
    expect(component['applied']()).toBe(original);
    expect(component['hasPending']()).toBe(true);
  });

  it('keeps the previous applied report when a request fails', async () => {
    const { component, api, messages } = await setup();
    const original = component['applied']();
    component['onView']('month');
    api.attendances.mockReturnValueOnce(throwError(() => new Error('No disponible')));
    await component['applyFilters']();
    expect(component['applied']()).toBe(original);
    expect(component['refreshing']()).toBe(false);
    expect(component['hasPending']()).toBe(true);
    expect(messages.add).toHaveBeenCalled();
  });

  it('exports the visible applied report while draft filters are pending', async () => {
    const { component, api } = await setup();
    vi.stubGlobal('URL', class extends URL {
      static override createObjectURL(): string { return 'blob:test-report'; }
      static override revokeObjectURL(): void { /* No live URL is created by this test. */ }
    });
    let downloadedName = '';
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      downloadedName = this.download;
    });
    const original = component['applied']();
    component['kind'].set('attendances');
    component['onFrom'](new Date(2025, 0, 1));
    component['exportReport']('xlsx');
    await vi.waitFor(() => expect(api.exportPurchaseOrders).toHaveBeenCalled());
    expect(api.exportPurchaseOrders).toHaveBeenCalledWith('xlsx', {
      date_from: original.from, date_to: original.to, branch_id: undefined,
    });
    expect(api.exportAttendances).not.toHaveBeenCalled();
    await vi.waitFor(() => expect(downloadedName).toBe('reporte-ordenes.xlsx'));
  });
});

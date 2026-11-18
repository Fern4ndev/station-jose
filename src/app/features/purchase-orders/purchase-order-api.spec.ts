import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { PurchaseOrderApi } from './purchase-order-api';

describe('PurchaseOrderApi', () => {
  it('sends search, pagination and supported filters', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(PurchaseOrderApi);
    const http = TestBed.inject(HttpTestingController);
    api.search('OC', 2, { branchId: 'branch', dateFrom: '2026-01-01', dateTo: '2026-12-31', sortBy: 'order_number', sortOrder: 'asc' }).subscribe();
    const request = http.expectOne((candidate) => candidate.url === '/api/v1/purchase-orders');
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('branch_id')).toBe('branch');
    expect(request.request.params.get('issue_date_from')).toBe('2026-01-01');
    expect(request.request.params.get('sort_by')).toBe('order_number');
    request.flush({ items: [], pagination: { page: 2, pages: 0, total: 0 } });
    http.verify();
  });
});

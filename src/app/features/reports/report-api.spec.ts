import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { ReportApi } from './report-api';

describe('ReportApi', () => {
  it('uses the same supported filters for reading and exporting', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(ReportApi);
    const http = TestBed.inject(HttpTestingController);
    const filters = { dateFrom: '2026-01-01', dateTo: '2026-01-31', branchId: 'branch' };
    api.get('attendances', filters).subscribe();
    const read = http.expectOne((request) => request.url === '/api/v1/reports/attendances');
    expect(read.request.params.get('date_from')).toBe('2026-01-01');
    expect(read.request.params.get('branch_id')).toBe('branch');
    read.flush({ items: [], total: 0, generated_at: '2026-01-31T00:00:00Z' });
    api.export('attendances', filters, 'xlsx').subscribe();
    const exportRequest = http.expectOne((request) => request.url === '/api/v1/reports/attendances/export');
    expect(exportRequest.request.responseType).toBe('blob');
    expect(exportRequest.request.params.get('date_from')).toBe('2026-01-01');
    expect(exportRequest.request.params.get('branch_id')).toBe('branch');
    expect(exportRequest.request.params.get('format')).toBe('xlsx');
    exportRequest.flush(new Blob());
    http.verify();
  });
});

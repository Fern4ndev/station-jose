import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { DashboardApi } from './dashboard-api';

describe('DashboardApi', () => {
  it('requests the dashboard and preserves decimal values from the API', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const http = TestBed.inject(HttpTestingController);
    let gallons = '';
    TestBed.inject(DashboardApi).getDashboard().subscribe((data) => gallons = data.attended_gallons);
    const request = http.expectOne('/api/v1/reports/dashboard');
    expect(request.request.method).toBe('GET');
    request.flush({ generated_at: '2026-01-01T00:00:00Z', orders: 1, vouchers: 1, attendances: 1,
      authorized_gallons: '10.000', attended_gallons: '5.250', available_gallons: '4.750', attended_amount: '50.00', by_fuel: [], by_period: [] });
    expect(gallons).toBe('5.250');
    http.verify();
  });
});

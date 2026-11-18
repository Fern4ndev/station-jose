import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { VoucherApi } from './voucher-api';

describe('VoucherApi', () => {
  it('sends only descriptive fields when correcting a voucher', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(VoucherApi);
    const http = TestBed.inject(HttpTestingController);
    api.correct('v1', { issuer_type: 'INSTITUTION', issuer_name: 'Entidad', voucher_number: '001' }).subscribe();
    const request = http.expectOne('/api/v1/vouchers/v1/descriptive-data');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ issuer_type: 'INSTITUTION', issuer_name: 'Entidad', voucher_number: '001' });
    request.flush({});
    http.verify();
  });
});

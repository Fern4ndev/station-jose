import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { OcrApi } from './ocr-api';

describe('OcrApi', () => {
  it('uploads a PDF and maps candidates for manual review', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(OcrApi);
    const http = TestBed.inject(HttpTestingController);
    const file = new File(['%PDF'], 'orden.pdf', { type: 'application/pdf' });
    let orderNumber: string | null = null;
    api.preview(file).subscribe((result) => orderNumber = result.fields.orderNumber);
    const request = http.expectOne('/api/v1/ocr/purchase-order-previews');
    expect(request.request.method).toBe('POST');
    expect((request.request.body as FormData).get('file')).toBe(file);
    request.flush({ fields: { order_number: 'OC-1', siaf_number: null, issue_date: null, institution_name: null, supplier_name: null, executing_unit: null, executing_unit_ruc: null, lines: [] }, unrecognized_fields: [], warnings: [] });
    expect(orderNumber).toBe('OC-1');
    http.verify();
  });
});

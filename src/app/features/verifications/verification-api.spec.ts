import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-url';
import { VerificationApi } from './verification-api';

describe('VerificationApi', () => {
  it('loads pending reviews and submits the chosen decision', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: '/api/v1' }] });
    const api = TestBed.inject(VerificationApi);
    const http = TestBed.inject(HttpTestingController);
    api.pending().subscribe();
    http.expectOne('/api/v1/verifications/pending').flush([]);
    api.verify('attendance-1', { decision: 'OBSERVED', observation: 'Firma ilegible' }).subscribe();
    const request = http.expectOne('/api/v1/attendances/attendance-1/verifications');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ decision: 'OBSERVED', observation: 'Firma ilegible' });
    request.flush({ id: 'verification-1' });
    http.verify();
  });
});

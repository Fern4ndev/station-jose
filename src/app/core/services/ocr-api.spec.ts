import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { extractApiError } from '../../shared/utils/api-error';
import { OcrApi } from './ocr-api';

describe('OcrApi', () => {
  let api: OcrApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(OcrApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.useRealTimers();
    TestBed.resetTestingModule();
  });

  it('cancela una carga sin respuesta y comunica el tiempo agotado', () => {
    vi.useFakeTimers();
    let message = '';
    api.analyze(new File(['%PDF'], 'orden.pdf', { type: 'application/pdf' })).subscribe({
      error: (error: unknown) => { message = extractApiError(error); },
    });
    const request = http.expectOne((request) => request.url.endsWith('/ocr/purchase-order-previews'));

    vi.advanceTimersByTime(75_000);

    expect(request.cancelled).toBe(true);
    expect(message).toContain('tiempo');
  });
});

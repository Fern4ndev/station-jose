import { HttpClient, HttpParams } from '@angular/common/http';
import { inject } from '@angular/core';
import type { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { cleanParams } from '../../shared/utils/query-params';

export function apiUrl(path = ''): string {
  return `${environment.apiUrl}${path}`;
}

export interface Page<T> {
  readonly items: T[];
  readonly total: number;
  readonly page: number;
  readonly page_size: number;
}

export interface ListParams {
  readonly page?: number;
  readonly page_size?: number;
  readonly q?: string | null;
  readonly [key: string]: unknown;
}

export function toParams(params?: ListParams): HttpParams {
  let http = new HttpParams();
  for (const [key, value] of Object.entries(cleanParams(params))) {
    http = http.set(key, String(value));
  }
  return http;
}

export abstract class BaseApi {
  protected readonly http = inject(HttpClient);

  protected get<T>(path: string, params?: ListParams): Observable<T> {
    return this.http.get<T>(apiUrl(path), { params: toParams(params) });
  }

  protected post<T>(path: string, body?: unknown): Observable<T> {
    return this.http.post<T>(apiUrl(path), body ?? {});
  }

  protected put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(apiUrl(path), body);
  }

  protected patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(apiUrl(path), body);
  }

  protected delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(apiUrl(path));
  }

  /** Subidas `multipart/form-data` (OCR, importaciones). */
  protected postForm<T>(path: string, formData: FormData): Observable<T> {
    return this.http.post<T>(apiUrl(path), formData);
  }

  /** POST con cabeceras puntuales, p. ej. `Idempotency-Key`. */
  protected postWithHeaders<T>(
    path: string,
    body: unknown,
    headers: Readonly<Record<string, string>>,
  ): Observable<T> {
    return this.http.post<T>(apiUrl(path), body, { headers });
  }

  /** Descargas binarias (PDF/Excel) sin exponer `HttpClient` a los hijos. */
  protected getBlob(path: string, params?: ListParams): Observable<Blob> {
    return this.http.get(apiUrl(path), {
      params: toParams(params),
      responseType: 'blob',
    });
  }
}

/** Rutas exactas del `openapi.json` (prefijo `/api/v1` viene de `environment.apiUrl`). */
export const API_ENDPOINTS = {
  health: {
    live: '/health/live',
    ready: '/health/ready',
  },
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    me: '/auth/me',
  },
  users: {
    base: '/users',
    byId: (userId: string) => `/users/${encodeURIComponent(userId)}`,
    role: (userId: string) => `/users/${encodeURIComponent(userId)}/role`,
    status: (userId: string) => `/users/${encodeURIComponent(userId)}/status`,
  },
  branches: '/branches',
  fuelTypes: '/fuel-types',
  purchaseOrders: {
    base: '/purchase-orders',
    byId: (orderId: string) => `/purchase-orders/${encodeURIComponent(orderId)}`,
    attendances: (orderId: string) =>
      `/purchase-orders/${encodeURIComponent(orderId)}/attendances`,
  },
  vouchers: {
    base: '/vouchers',
    attended: '/vouchers/attended',
    byId: (voucherId: string) => `/vouchers/${encodeURIComponent(voucherId)}`,
    descriptiveData: (voucherId: string) =>
      `/vouchers/${encodeURIComponent(voucherId)}/descriptive-data`,
    attendances: (voucherId: string) =>
      `/vouchers/${encodeURIComponent(voucherId)}/attendances`,
  },
  reports: {
    dashboard: '/reports/dashboard',
    purchaseOrders: '/reports/purchase-orders',
    purchaseOrdersExport: '/reports/purchase-orders/export',
    attendances: '/reports/attendances',
    attendancesExport: '/reports/attendances/export',
  },
  ocr: {
    purchaseOrderPreviews: '/ocr/purchase-order-previews',
  },
} as const;

/** Cabecera requerida por los dos endpoints de atenciones. */
export const IDEMPOTENCY_HEADER = 'Idempotency-Key';

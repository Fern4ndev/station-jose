import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../api/api-url';
import { authInterceptor } from '../../interceptors/auth.interceptor';
import { AuthApiService, AuthStore } from './auth';

describe('AuthApiService', () => {
  let http: HttpTestingController;
  let api: AuthApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideRouter([]),
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      { provide: API_BASE_URL, useValue: '/api/v1' },
    ] });
    http = TestBed.inject(HttpTestingController);
    api = TestBed.inject(AuthApiService);
  });

  afterEach(() => http.verify());

  it('posts normalized credentials and maps the session returned by the API', () => {
    let token = '';
    api.login({ email: '  ADMIN@EXAMPLE.COM ', password: 'password123' }).subscribe((result) => token = result.accessToken);
    const request = http.expectOne('/api/v1/auth/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ email: 'admin@example.com', password: 'password123' });
    request.flush({ access_token: 'token', token_type: 'bearer', expires_in: 60, permissions: ['reports.read'], user: {
      id: '1', first_name: 'Ana', last_name: 'Pérez', dni: '12345678', email: 'admin@example.com', role: 'ADMIN', branch: null, is_active: true,
    } });
    expect(token).toBe('token');
  });

  it('sends the bearer token to the API when closing the session', () => {
    const store = TestBed.inject(AuthStore);
    store.setSession({ accessToken: 'token', expiresIn: 60, permissions: [], user: {
      id: '1', firstName: 'Ana', lastName: 'Pérez', dni: '12345678', email: 'admin@example.com', role: 'ADMIN', branch: null, isActive: true,
    } });
    api.logout().subscribe();
    const request = http.expectOne('/api/v1/auth/logout');
    expect(request.request.headers.get('Authorization')).toBe('Bearer token');
    request.flush(null, { status: 204, statusText: 'No Content' });
    store.clearSession();
  });
});

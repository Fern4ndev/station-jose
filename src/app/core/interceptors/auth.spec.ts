import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { environment } from '../../../environments/environment';
import type { TokenResponse } from '../models/auth.model';
import type { ApiError } from '../models/error.model';
import { AuthService } from '../services/auth.service';
import { TokenStorageService } from '../services/token-storage.service';
import { authInterceptor, isApiRequest, isAuthEndpoint } from './auth';

const api = (path: string) => `${environment.apiUrl}${path}`;

const setup = (token: string | null = 'token-abc') => {
  const accessToken = signal<string | null>(token);
  const auth = {
    accessToken,
    isAuthenticated: vi.fn(() => accessToken() !== null),
    handleSessionExpired: vi.fn(),
  };

  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      { provide: AuthService, useValue: auth },
    ],
  });

  return {
    auth,
    http: TestBed.inject(HttpClient),
    controller: TestBed.inject(HttpTestingController),
  };
};

describe('authInterceptor', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('adjunta el Bearer solo a peticiones de la API', () => {
    const { http, controller } = setup();

    http.get(api('/users')).subscribe();
    const request = controller.expectOne(api('/users'));

    expect(request.request.headers.get('Authorization')).toBe('Bearer token-abc');
    request.flush([]);
    controller.verify();
  });

  it('no adjunta cabecera cuando no hay token', () => {
    const { http, controller } = setup(null);

    http.get(api('/users')).subscribe();
    const request = controller.expectOne(api('/users'));

    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush([]);
    controller.verify();
  });

  it('ignora URLs externas: sin token y sin cerrar la sesión ante un 401', () => {
    const { http, controller, auth } = setup();

    http.get('https://externo.test/data').subscribe({ error: () => undefined });
    const request = controller.expectOne('https://externo.test/data');

    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(auth.handleSessionExpired).not.toHaveBeenCalled();
    controller.verify();
  });

  it('no adjunta token al endpoint de login', () => {
    const { http, controller } = setup();

    http.post(api('/auth/login'), {}).subscribe();
    const request = controller.expectOne(api('/auth/login'));

    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({});
    controller.verify();
  });

  it('ante un 401 en la API cierra la sesión y propaga el ApiError', () => {
    const { http, controller, auth } = setup();
    let failure: ApiError | undefined;

    http.get(api('/users')).subscribe({ error: (error: ApiError) => (failure = error) });
    controller
      .expectOne(api('/users'))
      .flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.handleSessionExpired).toHaveBeenCalledTimes(1);
    expect(failure?.status).toBe(401);
    expect(failure?.code).toBe('HTTP_ERROR');
    controller.verify();
  });

  it('un 401 en el login se normaliza pero no cierra la sesión', () => {
    const { http, controller, auth } = setup(null);
    let failure: ApiError | undefined;

    http
      .post(api('/auth/login'), {})
      .subscribe({ error: (error: ApiError) => (failure = error) });
    controller.expectOne(api('/auth/login')).flush(
      { success: false, error: { code: 'INVALID_CREDENTIALS', message: 'Credenciales inválidas' } },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(auth.handleSessionExpired).not.toHaveBeenCalled();
    expect(failure?.status).toBe(401);
    expect(failure?.message).toBe('Credenciales inválidas');
    controller.verify();
  });

  it('normaliza un 500 sin tocar la sesión', () => {
    const { http, controller, auth } = setup();
    let failure: ApiError | undefined;

    http.get(api('/orders')).subscribe({ error: (error: ApiError) => (failure = error) });
    controller
      .expectOne(api('/orders'))
      .flush(null, { status: 500, statusText: 'Server Error' });

    expect(auth.handleSessionExpired).not.toHaveBeenCalled();
    expect(failure?.code).toBe('INTERNAL_SERVER_ERROR');
    controller.verify();
  });

  it('normaliza un 422 con el detalle de validación de FastAPI', () => {
    const { http, controller } = setup();
    let failure: ApiError | undefined;

    http.post(api('/vouchers'), {}).subscribe({ error: (error: ApiError) => (failure = error) });
    controller.expectOne(api('/vouchers')).flush(
      { detail: [{ loc: ['body', 'voucher_number'], msg: 'Requerido', type: 'missing' }] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    expect(failure?.code).toBe('VALIDATION_ERROR');
    expect(failure?.message).toContain('voucher_number: Requerido');
    controller.verify();
  });

  it('ante un 401 limpia la sesión y redirige a /login?reason=session_expired', () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });

    const session: TokenResponse = {
      access_token: 'jwt-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'user-1',
        first_name: 'Ana',
        last_name: 'Pérez',
        dni: '12345678',
        email: 'ana@estacion.test',
        role: 'OFFICE',
        branch: null,
        is_active: true,
      },
      permissions: [],
    };
    const storage = TestBed.inject(TokenStorageService);
    storage.save(session, false);

    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const http = TestBed.inject(HttpClient);
    const controller = TestBed.inject(HttpTestingController);

    http.get(api('/users')).subscribe({ error: () => undefined });
    const request = controller.expectOne(api('/users'));
    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-token');
    request.flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(storage.token()).toBeNull();
    expect(storage.user()).toBeNull();
    expect(navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { reason: 'session_expired' },
    });
    controller.verify();
  });

  it('detecta API y endpoints de auth por URL', () => {
    expect(isApiRequest(api('/users'))).toBe(true);
    expect(isApiRequest('https://externo.test')).toBe(false);
    expect(isAuthEndpoint(api('/auth/login'))).toBe(true);
    expect(isAuthEndpoint(api('/auth/logout'))).toBe(true);
    expect(isAuthEndpoint(api('/auth/me'))).toBe(false);
  });
});

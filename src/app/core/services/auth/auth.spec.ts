import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { environment } from '../../../../environments/environment';
import { AUTH_STORAGE_KEYS } from '../../constants/auth-storage';
import type { CurrentUserOut, LoginResponse, UserOut } from '../../models/user';
import { authInterceptor } from '../../interceptors/auth';
import { AuthService } from './auth';

const api = (path: string) => `${environment.apiUrl}${path}`;

const user: UserOut = {
  id: 'user-1',
  first_name: 'Ana',
  last_name: 'Pérez',
  dni: '12345678',
  email: 'ana@estacion.test',
  role: 'OFFICE',
  branch: null,
  is_active: true,
};

const loginResponse: LoginResponse = {
  access_token: 'jwt-token',
  token_type: 'bearer',
  expires_in: 3600,
  user,
  permissions: ['reports.read'],
};

const seedSession = (expiresInMs: number): CurrentUserOut => {
  const sessionUser: CurrentUserOut = { ...user, permissions: ['reports.read'] };
  localStorage.setItem(AUTH_STORAGE_KEYS.accessToken, 'jwt-token');
  localStorage.setItem(AUTH_STORAGE_KEYS.expiresAt, String(Date.now() + expiresInMs));
  localStorage.setItem(AUTH_STORAGE_KEYS.session, JSON.stringify(sessionUser));
  localStorage.setItem(AUTH_STORAGE_KEYS.persistence, 'local');
  return sessionUser;
};

const setup = () => {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
    ],
  });

  const router = TestBed.inject(Router);
  vi.spyOn(router, 'navigate').mockResolvedValue(true);
  vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

  return {
    auth: TestBed.inject(AuthService),
    http: TestBed.inject(HttpClient),
    controller: TestBed.inject(HttpTestingController),
    router,
  };
};

describe('AuthService', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('initialize sin sesión deja el estado limpio y completa sin HTTP', () => {
    const { auth, controller } = setup();
    let completed = false;

    auth.initialize().subscribe({ complete: () => (completed = true) });

    expect(completed).toBe(true);
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.accessToken()).toBeNull();
    controller.expectNone(api('/auth/me'));
    controller.verify();
  });

  it('initialize con access token vigente hidrata la sesión sin HTTP', () => {
    const sessionUser = seedSession(60_000);
    const { auth, controller } = setup();
    let completed = false;

    auth.initialize().subscribe({ complete: () => (completed = true) });

    expect(completed).toBe(true);
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.currentUser()).toEqual(sessionUser);
    expect(auth.isOffice()).toBe(true);
    expect(auth.userInitials()).toBe('AP');
    controller.verify();
  });

  it('initialize descarta un access token vencido y limpia el storage', () => {
    seedSession(-1_000);
    const { auth, controller } = setup();

    auth.initialize().subscribe();

    expect(auth.isAuthenticated()).toBe(false);
    expect(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken)).toBeNull();
    expect(localStorage.getItem(AUTH_STORAGE_KEYS.session)).toBeNull();
    controller.verify();
  });

  it('login envía JSON, persiste la sesión y navega al inicio del rol', () => {
    const { auth, http, controller, router } = setup();
    let result: CurrentUserOut | undefined;

    auth
      .login({ email: ' ana@estacion.test ', password: 'secreto123', remember: true })
      .subscribe((value) => (result = value));

    const request = controller.expectOne(api('/auth/login'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      email: 'ana@estacion.test',
      password: 'secreto123',
    });
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush(loginResponse);

    expect(result?.permissions).toEqual(['reports.read']);
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.accessToken()).toBe('jwt-token');
    expect(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken)).toBe('jwt-token');
    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
    controller.verify();
  });

  it('login usa sessionStorage cuando no se recuerda la sesión', () => {
    const { auth, controller } = setup();

    auth.login({ email: 'ana@estacion.test', password: 'secreto123', remember: false }).subscribe();
    controller.expectOne(api('/auth/login')).flush(loginResponse);

    expect(sessionStorage.getItem(AUTH_STORAGE_KEYS.accessToken)).toBe('jwt-token');
    expect(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken)).toBeNull();
  });

  it('login sin user en la respuesta lo completa con /auth/me', () => {
    const { auth, controller } = setup();
    const { user: _omitted, ...withoutUser } = loginResponse;

    auth.login({ email: 'ana@estacion.test', password: 'secreto123', remember: true }).subscribe();
    controller.expectOne(api('/auth/login')).flush(withoutUser);

    const me = controller.expectOne(api('/auth/me'));
    me.flush({ ...user, permissions: ['reports.read'] });

    expect(auth.currentUser()?.first_name).toBe('Ana');
    expect(auth.accessToken()).toBe('jwt-token');
    controller.verify();
  });

  it('un 401 de login cuenta el intento sin cerrar la sesión', () => {
    const { auth, controller } = setup();

    auth.login({ email: 'ana@estacion.test', password: 'mala', remember: true }).subscribe({
      error: () => undefined,
    });
    controller
      .expectOne(api('/auth/login'))
      .flush({ detail: 'Credenciales inválidas' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.failedAttempts()).toBe(1);
    expect(auth.isLockedOut()).toBe(false);
    expect(auth.currentUser()).toBeNull();
  });

  it('bloquea tras 5 fallos y responde 429 sin hacer HTTP', async () => {
    const { auth, controller } = setup();

    for (let attempt = 0; attempt < 5; attempt += 1) {
      auth.login({ email: 'ana@estacion.test', password: 'mala', remember: true }).subscribe({
        error: () => undefined,
      });
      controller
        .expectOne(api('/auth/login'))
        .flush(null, { status: 401, statusText: 'Unauthorized' });
    }

    expect(auth.isLockedOut()).toBe(true);
    await expect(
      firstValueFrom(
        auth.login({ email: 'ana@estacion.test', password: 'mala', remember: true }),
      ),
    ).rejects.toMatchObject({ status: 429 });
    controller.expectNone(api('/auth/login'));
    controller.verify();
  });

  it('logout limpia de inmediato, revoca con Bearer y navega al login', () => {
    seedSession(60_000);
    const { auth, controller, router } = setup();

    auth.logout();

    expect(auth.isAuthenticated()).toBe(false);
    expect(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken)).toBeNull();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);

    const request = controller.expectOne(api('/auth/logout'));
    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-token');
    request.flush(null, { status: 204, statusText: 'No Content' });
    controller.verify();
  });

  it('handleSessionExpired limpia y navega una sola vez', () => {
    seedSession(60_000);
    const { auth, router } = setup();

    auth.handleSessionExpired();
    auth.handleSessionExpired();

    expect(auth.isAuthenticated()).toBe(false);
    expect(router.navigate).toHaveBeenCalledTimes(1);
    expect(router.navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { reason: 'session_expired' },
    });
  });

  it('me actualiza usuario y permisos manteniendo el token', () => {
    seedSession(60_000);
    const { auth, controller } = setup();

    auth.me().subscribe();
    controller
      .expectOne(api('/auth/me'))
      .flush({ ...user, first_name: 'María', permissions: ['users.manage'] });

    expect(auth.currentUser()?.first_name).toBe('María');
    expect(auth.permissions()).toEqual(['users.manage']);
    expect(auth.accessToken()).toBe('jwt-token');
    controller.verify();
  });

  it('resetAttempts limpia el bloqueo', () => {
    const { auth } = setup();

    auth.registerFailure();
    auth.registerFailure();
    expect(auth.failedAttempts()).toBe(2);

    auth.resetAttempts();
    expect(auth.failedAttempts()).toBe(0);
    expect(auth.isLockedOut()).toBe(false);
  });
});

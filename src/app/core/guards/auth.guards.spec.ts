import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { AuthStore } from '../services/auth/auth';
import { authGuard, permissionGuard } from './auth.guards';

describe('route access', () => {
  let store: AuthStore;
  let router: Router;
  const route = (permission?: string): ActivatedRouteSnapshot => ({ data: permission ? { permission } : {} }) as ActivatedRouteSnapshot;
  const state = { url: '/app/users' } as RouterStateSnapshot;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    store = TestBed.inject(AuthStore);
    router = TestBed.inject(Router);
  });
  afterEach(() => store.clearSession());

  function session(role: 'ADMIN' | 'OFFICE' | 'ATTENDANT', permissions: string[]): void {
    store.setSession({ accessToken: 'test', expiresIn: 60, permissions, user: {
      id: '1', firstName: 'Usuario', lastName: 'Prueba', dni: '12345678', email: 'test@example.com',
      role, branch: null, isActive: true,
    } });
  }

  it('redirects an unauthenticated visitor to login preserving the requested route', () => {
    const result = TestBed.runInInjectionContext(() => authGuard(route(), state)) as UrlTree;
    expect(router.serializeUrl(result)).toBe('/auth/login?returnUrl=%2Fapp%2Fusers');
  });

  it.each([
    ['ADMIN', ['users.manage', 'reports.read', 'attendances.create'], true, true, true],
    ['OFFICE', ['reports.read'], false, true, false],
    ['ATTENDANT', ['attendances.create'], false, false, true],
  ] as const)('%s checks each permission', (role, permissions, users, reports, attendances) => {
    session(role, [...permissions]);
    for (const [permission, allowed] of [['users.manage', users], ['reports.read', reports], ['attendances.create', attendances]] as const) {
      const result = TestBed.runInInjectionContext(() => permissionGuard(route(permission), state));
      if (allowed) expect(result).toBe(true);
      else expect(router.serializeUrl(result as UrlTree)).toBe('/access-denied');
    }
  });

  it('denies a protected route without a declared permission', () => {
    session('ADMIN', ['users.manage']);
    const result = TestBed.runInInjectionContext(() => permissionGuard(route(), state)) as UrlTree;
    expect(router.serializeUrl(result)).toBe('/access-denied');
  });
});

import { computed, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, type ActivatedRouteSnapshot, type CanActivateFn, type RouterStateSnapshot, type UrlTree } from '@angular/router';
import { MessageService } from 'primeng/api';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NAV, ROLE_HOME, navForRole, rolesForRoute } from '../constants/nav';
import type { UserOut, UserRole } from '../models/user';
import { AuthService } from '../services/auth/auth';
import { authGuard, loginGuard, navGuard } from './auth-guard';

const userFor = (role: UserRole): UserOut => ({
  id: `user-${role}`,
  first_name: 'Ana',
  last_name: 'Pérez',
  dni: '12345678',
  email: 'ana@estacion.test',
  role,
  branch: null,
  is_active: true,
});

const routeSnapshot = {} as ActivatedRouteSnapshot;
const routerState = { url: '/ordenes' } as RouterStateSnapshot;

const pathsFor = (role: UserRole): string[] =>
  navForRole(role).flatMap((entry) =>
    'children' in entry ? entry.children.map((child) => child.path) : [entry.path],
  );

const setup = (role: UserRole | null) => {
  const user = signal<UserOut | null>(role ? userFor(role) : null);
  const auth = {
    user,
    role: computed(() => user()?.role ?? null),
    isAuthenticated: vi.fn(() => user() !== null),
  };
  const messages = { add: vi.fn() };

  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: AuthService, useValue: auth },
      { provide: MessageService, useValue: messages },
    ],
  });

  return { auth, messages };
};

const run = (guard: CanActivateFn) =>
  TestBed.runInInjectionContext(() => guard(routeSnapshot, routerState));

describe('auth guards', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('authGuard redirige a /login cuando no hay sesión', () => {
    setup(null);

    const result = run(authGuard);

    expect(result).toBeInstanceOf(Object);
    expect((result as UrlTree).toString()).toBe('/login');
  });

  it('authGuard permite el acceso con sesión activa', () => {
    setup('ATTENDANT');

    expect(run(authGuard)).toBe(true);
  });

  it.each(['ADMIN', 'OFFICE', 'ATTENDANT'] as const)(
    'loginGuard devuelve a %s a su ROLE_HOME',
    (role) => {
      setup(role);

      const result = run(loginGuard);

      expect((result as UrlTree).toString()).toBe(ROLE_HOME[role]);
    },
  );

  it('loginGuard deja pasar a un usuario anónimo', () => {
    setup(null);

    expect(run(loginGuard)).toBe(true);
  });

  it('navGuard bloquea a OFFICE en /usuarios, avisa y lo devuelve a su inicio', () => {
    const { messages } = setup('OFFICE');

    const result = run(navGuard('/usuarios'));

    expect((result as UrlTree).toString()).toBe(ROLE_HOME.OFFICE);
    expect(messages.add).toHaveBeenCalledTimes(1);
    expect(messages.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'warn',
        summary: 'Acceso restringido',
        detail: 'No tienes acceso a esa sección.',
      }),
    );
  });

  it('navGuard bloquea a ATTENDANT en /reportes y lo devuelve a atenciones', () => {
    const { messages } = setup('ATTENDANT');

    const result = run(navGuard('/reportes'));

    expect((result as UrlTree).toString()).toBe('/atenciones');
    expect(messages.add).toHaveBeenCalledOnce();
  });

  it('navGuard permite las rutas propias y compartidas de cada rol', () => {
    setup('ATTENDANT');
    expect(run(navGuard('/atenciones'))).toBe(true);
    expect(run(navGuard('/ordenes'))).toBe(true);
    expect(run(navGuard('/vales'))).toBe(true);
    expect(run(navGuard('/'))).toBe(true);

    TestBed.resetTestingModule();
    setup('OFFICE');
    expect(run(navGuard('/reportes'))).toBe(true);
    expect(run(navGuard('/ordenes'))).toBe(true);

    TestBed.resetTestingModule();
    setup('ADMIN');
    expect(run(navGuard('/usuarios'))).toBe(true);
    expect(run(navGuard('/reportes'))).toBe(true);
  });

  it('navGuard manda al login si no hay sesión', () => {
    setup(null);

    expect((run(navGuard('/ordenes')) as UrlTree).toString()).toBe('/login');
  });

  it('navForRole expone solo las secciones de cada rol real', () => {
    expect(pathsFor('ADMIN')).toEqual(['/', '/ordenes', '/vales', '/atenciones', '/reportes', '/usuarios']);
    expect(pathsFor('OFFICE')).toEqual(['/', '/ordenes', '/vales', '/atenciones', '/reportes']);
    expect(pathsFor('ATTENDANT')).toEqual(['/', '/ordenes', '/vales', '/atenciones']);
    expect(navForRole(undefined)).toEqual([]);
  });

  it('rolesForRoute coincide con los roles declarados en NAV', () => {
    expect(rolesForRoute('/usuarios')).toEqual(['ADMIN']);
    expect(rolesForRoute('/reportes')).toEqual(['ADMIN', 'OFFICE']);
    expect(rolesForRoute('/ordenes')).toEqual(['ADMIN', 'OFFICE', 'ATTENDANT']);

    const children = NAV.flatMap((entry) => ('children' in entry ? entry.children : [entry]));
    for (const child of children) {
      expect(rolesForRoute(child.path)).toEqual([...child.roles]);
    }
  });
});

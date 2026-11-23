import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { MessageService } from 'primeng/api';
import { APP_ROUTES, ROLE_HOME, rolesForRoute } from '../constants/nav';
import type { UserRole } from '../models/user';
import { AuthService } from '../services/auth/auth';

/** Ruta inicial del rol; sin rol, el login. */
export const homeFor = (role: UserRole | undefined): string =>
  role ? ROLE_HOME[role] : APP_ROUTES.login;

/** Exige sesión activa para el layout protegido. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isAuthenticated() ? true : inject(Router).createUrlTree([APP_ROUTES.login]);
};

/** Un usuario autenticado no vuelve a la pantalla de login. */
export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (!auth.isAuthenticated()) {
    return true;
  }
  return inject(Router).createUrlTree([homeFor(auth.role() ?? undefined)]);
};

/**
 * Autoriza según los roles indicados. Sin permiso avisa con un toast y devuelve
 * al usuario a la ruta inicial de su rol.
 */
export const roleGuard =
  (...allowedRoles: readonly UserRole[]): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (!auth.isAuthenticated()) {
      return router.createUrlTree([APP_ROUTES.login]);
    }

    const role = auth.role() ?? undefined;
    if (role && allowedRoles.includes(role)) {
      return true;
    }

    inject(MessageService).add({
      severity: 'warn',
      summary: 'Acceso restringido',
      detail: 'No tienes acceso a esa sección.',
    });
    return router.createUrlTree([homeFor(role)]);
  };

/** Conecta una ruta con los roles declarados en `constants/nav.ts`. */
export const navGuard = (route: string): CanActivateFn => roleGuard(...rolesForRoute(route));

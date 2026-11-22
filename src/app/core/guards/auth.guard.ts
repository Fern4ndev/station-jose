import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { map } from 'rxjs';
import { APP_ROUTES, SESSION_EXPIRED_REASON } from '../constants/system.constants';
import { AuthService } from '../services/auth.service';

/**
 * Exige sesión activa para `layouts/admin`.
 * Si hay token pero el backend lo rechaza, limpia la sesión y vuelve al login
 * conservando la ruta solicitada en `returnUrl`.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const redirect = (reason?: string) =>
    router.createUrlTree([APP_ROUTES.login], {
      queryParams: reason ? { returnUrl: state.url, reason } : { returnUrl: state.url },
    });

  if (!auth.token()) {
    return redirect();
  }

  return auth
    .checkAuthStatus()
    .pipe(map((valid) => (valid ? true : redirect(SESSION_EXPIRED_REASON))));
};

import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { APP_ROUTES } from '../constants/system.constants';
import { AuthService } from '../services/auth.service';

/** Un usuario con sesión activa no vuelve a `layouts/auth`. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isAuthenticated() ? inject(Router).createUrlTree([APP_ROUTES.dashboard]) : true;
};

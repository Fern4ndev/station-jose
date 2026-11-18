import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { homePathForPermissions, safeReturnUrl } from '../models/auth.models';
import { AuthStore } from '../services/auth/auth';

export const authGuard: CanActivateFn = (_route, state) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(['/auth/login'], {
    queryParams: { returnUrl: state.url },
  });
};

export const guestGuard: CanActivateFn = (route) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);
  const user = authStore.user();

  if (!user) {
    return true;
  }

  const returnUrl = route.queryParamMap.get('returnUrl');
  const destination = safeReturnUrl(returnUrl) ?? homePathForPermissions(authStore.permissions());
  return router.parseUrl(destination);
};

export const permissionGuard: CanActivateFn = (route) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);
  const permission: unknown = route.data['permission'];

  if (typeof permission === 'string' && authStore.hasPermission(permission)) {
    return true;
  }

  return router.parseUrl('/access-denied');
};

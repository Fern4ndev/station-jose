import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';

/**
 * La vista de usuarios solo se sirve al Administrador. El menú ya oculta la
 * sección para los demás roles; este guard corta además el acceso directo por
 * URL antes de montar la vista.
 */
export const adminOnlyGuard: CanActivateFn = () =>
  inject(AdminUiState).role() === 'ADMIN' ? true : inject(Router).createUrlTree(['/']);

import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { APP_ROUTES, PERMISSIONS } from '../constants/system.constants';
import type { Permission } from '../models/auth.model';
import { AuthService } from '../services/auth.service';

/**
 * Deja pasar si la sesión tiene al menos uno de los permisos indicados.
 * Se evalúa contra `permissions` del JWT guardado, así que la misma sesión
 * gobierna guard, menú y navegación directa por URL.
 */
export const permissionGuard =
  (...permissions: readonly Permission[]): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    const allowed = permissions.some((permission) => auth.hasPermission(permission));
    return allowed ? true : inject(Router).createUrlTree([APP_ROUTES.dashboard]);
  };

/** Gestión de usuarios: exige `users.manage`, que el backend solo da a ADMIN. */
export const adminOnlyGuard = permissionGuard(PERMISSIONS.usersManage);

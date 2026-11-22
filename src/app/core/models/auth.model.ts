import type { UserResponse } from './user.model';

/** `UserRole` de `app/core/permissions.py`. */
export type UserRole = 'ADMIN' | 'OFFICE' | 'ATTENDANT';

/**
 * Permisos versionados que expone el backend en `permissions`.
 * Se tipan como unión para que `hasPermission()` detecte errores de tipeo.
 */
export type Permission =
  | 'users.manage'
  | 'purchase_orders.read'
  | 'purchase_orders.create'
  | 'purchase_orders.update'
  | 'purchase_orders.delete'
  | 'vouchers.read'
  | 'vouchers.correct_descriptive'
  | 'vouchers.delete'
  | 'attendances.create'
  | 'attendances.read_own'
  | 'attendances.read_all'
  | 'balances.read'
  | 'reports.read'
  | 'reports.export'
  | 'ocr.purchase_orders.process';

export interface LoginRequest {
  readonly email: string;
  readonly password: string;
}

/** `TokenResponse` de `app/schemas/auth.py`. */
export interface TokenResponse {
  readonly access_token: string;
  readonly token_type: string;
  readonly expires_in: number;
  readonly user: UserResponse;
  readonly permissions: readonly Permission[];
}

/** `CurrentUserResponse`: el usuario más sus permisos efectivos. */
export interface CurrentUserResponse extends UserResponse {
  readonly permissions: readonly Permission[];
}

/** Credenciales que llegan desde el formulario de login. */
export interface LoginCredentials {
  readonly email: string;
  readonly password: string;
  /** true → localStorage; false → sessionStorage. */
  readonly remember: boolean;
}

/** Sesión ya normalizada y persistida en el navegador. */
export interface AuthSession {
  readonly token: string;
  readonly tokenType: string;
  readonly expiresAt: number;
  readonly user: CurrentUserResponse;
  readonly permissions: readonly Permission[];
  readonly remember: boolean;
}

/** Datos que se serializan en el almacenamiento (sin duplicar permisos). */
export interface StoredSession {
  readonly token: string;
  readonly tokenType: string;
  readonly expiresAt: number;
  readonly user: CurrentUserResponse;
  readonly remember: boolean;
}


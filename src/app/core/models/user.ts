import type { BranchSummary } from './catalog';
import type { PaginatedResponse } from './pagination';

/** `UserRole` de `app/core/permissions.py`. */
export type UserRole = 'ADMIN' | 'OFFICE' | 'ATTENDANT';

/**
 * Permisos versionados que expone el backend en `permissions`.
 * Unión literal para que `hasPermission()` detecte errores de tipeo.
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

/** `UserResponse`: usuario tal como lo devuelve FastAPI. */
export interface UserOut {
  readonly id: string;
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly role: UserRole;
  readonly branch: BranchSummary | null;
  readonly is_active: boolean;
}

/** `CurrentUserResponse`: el usuario más sus permisos efectivos. */
export interface CurrentUserOut extends UserOut {
  readonly permissions: readonly Permission[];
}

export interface UserCreate {
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly password: string;
  readonly role: UserRole;
  readonly branch_id?: string | null;
}

export interface UserUpdate {
  readonly first_name?: string | null;
  readonly last_name?: string | null;
}

export interface UserRoleUpdate {
  readonly role: UserRole;
  readonly branch_id?: string | null;
}

export interface UserStatusUpdate {
  readonly is_active: boolean;
}

export type UserListResponse = PaginatedResponse<UserOut>;

export type UserListQuery = {
  readonly page?: number;
  readonly page_size?: number;
};

/** `LoginRequest` de `POST /auth/login`. */
export interface LoginRequest {
  readonly email: string;
  readonly password: string;
}

/** `TokenResponse` de `POST /auth/login`. */
export interface LoginResponse {
  readonly access_token: string;
  readonly token_type?: string;
  readonly expires_in: number;
  readonly user: UserOut;
  readonly permissions: readonly Permission[];
}

/** Credenciales que llegan desde el formulario de login (modelo de cliente). */
export interface LoginCredentials {
  readonly email: string;
  readonly password: string;
  /** true → localStorage; false → sessionStorage. */
  readonly remember: boolean;
  /** Ruta interna solicitada antes del login; si falta, se usa `ROLE_HOME`. */
  readonly returnUrl?: string;
}

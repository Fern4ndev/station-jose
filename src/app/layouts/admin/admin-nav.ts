import type { Permission } from '../../core/models/auth.model';
import type { UiIconName } from '../../shared/components/ui-icon/ui-icon';

export type PageId = 'dashboard' | 'orders' | 'vouchers' | 'attendances' | 'reports' | 'users';

export interface AdminNavItem {
  readonly id: PageId;
  readonly label: string;
  readonly icon: UiIconName;
  /** Permisos del JWT que habilitan la sección; basta con tener uno. */
  readonly permissions: readonly Permission[];
}

/** Cuenta ya derivada de `AuthService` para pintar el armazón. */
export interface AdminUser {
  readonly name: string;
  readonly initials: string;
  readonly label: string;
}

/**
 * Menú del panel. La visibilidad la decide el permiso que el backend emite en
 * `permissions` al iniciar sesión, no el rol.
 */
export const ADMIN_NAV: readonly AdminNavItem[] = [
  {
    id: 'dashboard',
    label: 'Panel de control',
    icon: 'dashboard',
    permissions: ['balances.read'],
  },
  {
    id: 'orders',
    label: 'Órdenes de compra',
    icon: 'orders',
    permissions: ['purchase_orders.read'],
  },
  { id: 'vouchers', label: 'Vales', icon: 'vouchers', permissions: ['vouchers.read'] },
  {
    id: 'attendances',
    label: 'Atenciones',
    icon: 'attendances',
    permissions: ['attendances.read_own', 'attendances.read_all'],
  },
  { id: 'reports', label: 'Reportes', icon: 'reports', permissions: ['reports.read'] },
  { id: 'users', label: 'Usuarios', icon: 'users', permissions: ['users.manage'] },
];

export const PAGE_PATHS: Readonly<Record<PageId, string>> = {
  dashboard: '',
  orders: 'ordenes',
  vouchers: 'vales',
  attendances: 'atenciones',
  reports: 'reportes',
  users: 'usuarios',
};

export const pageFromUrl = (url: string): PageId => {
  const path = url.split('?')[0].split('#')[0].replace(/^\/+|\/+$/g, '');
  const match = (Object.keys(PAGE_PATHS) as PageId[]).find((id) => PAGE_PATHS[id] === path);
  return match ?? 'dashboard';
};

export const PAGE_LABELS: Readonly<Record<PageId, string>> = {
  dashboard: 'Panel de control',
  orders: 'Órdenes de compra',
  vouchers: 'Vales',
  attendances: 'Atenciones',
  reports: 'Reportes',
  users: 'Usuarios',
};

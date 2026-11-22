import type { UiIconName } from '../../shared/components/ui-icon/ui-icon';

export type DemoRole = 'OFFICE' | 'ADMIN' | 'ATTENDANT';

export type PageId = 'dashboard' | 'orders' | 'vouchers' | 'attendances' | 'reports' | 'users';

export interface AdminNavItem {
  readonly id: PageId;
  readonly label: string;
  readonly icon: UiIconName;
  readonly roles: readonly DemoRole[];
}

export interface DemoUser {
  readonly name: string;
  readonly initials: string;
  readonly label: string;
}

export const ADMIN_NAV: readonly AdminNavItem[] = [
  { id: 'dashboard', label: 'Panel de control', icon: 'dashboard', roles: ['OFFICE', 'ADMIN', 'ATTENDANT'] },
  { id: 'orders', label: 'Órdenes de compra', icon: 'orders', roles: ['OFFICE', 'ADMIN', 'ATTENDANT'] },
  { id: 'vouchers', label: 'Vales', icon: 'vouchers', roles: ['OFFICE', 'ADMIN', 'ATTENDANT'] },
  { id: 'attendances', label: 'Atenciones', icon: 'attendances', roles: ['ADMIN', 'ATTENDANT'] },
  { id: 'reports', label: 'Reportes', icon: 'reports', roles: ['OFFICE', 'ADMIN'] },
  { id: 'users', label: 'Usuarios', icon: 'users', roles: ['ADMIN'] },
];

export const ROLE_USERS: Readonly<Record<DemoRole, DemoUser>> = {
  OFFICE: { name: 'María Paredes', initials: 'MP', label: 'Personal de oficina' },
  ADMIN: { name: 'Carlos Mendoza', initials: 'CM', label: 'Administrador' },
  ATTENDANT: { name: 'Luis Cárdenas', initials: 'LC', label: 'Grifero · San José' },
};

export const ROLE_OPTIONS: readonly { value: DemoRole; label: string }[] = [
  { value: 'OFFICE', label: 'Vista de oficina' },
  { value: 'ADMIN', label: 'Vista de administrador' },
  { value: 'ATTENDANT', label: 'Vista de grifero' },
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

import type { Permission, UserRole } from '../models/user';
import type { UiIconName } from '../../shared/components/ui-icon/ui-icon';

/** El panel (`layouts/admin`) cuelga de la raíz; se deja explícito para componer rutas. */
export const ADMIN_PREFIX = '';

export interface NavChild {
  readonly id: string;
  readonly label: string;
  readonly icon: UiIconName;
  readonly path: string;
  readonly roles: readonly UserRole[];
  /** Solo visibilidad en el sidebar; no cambia el acceso a la ruta. */
  readonly hiddenFor?: readonly UserRole[];
}

export interface NavGroup {
  readonly id: string;
  readonly label: string;
  readonly children: readonly NavChild[];
}

export type NavEntry = NavChild | NavGroup;

const ALL_ROLES: readonly UserRole[] = ['ADMIN', 'OFFICE', 'ATTENDANT'];

/** Ruta inicial de cada rol al iniciar sesión. */
export const ROLE_HOME: Record<UserRole, string> = {
  ADMIN: `${ADMIN_PREFIX}/`,
  OFFICE: `${ADMIN_PREFIX}/`,
  ATTENDANT: `${ADMIN_PREFIX}/atenciones`,
};

/** Rutas de la aplicación (las que existen en `app.routes.ts`). */
export const APP_ROUTES = {
  login: '/login',
  dashboard: '/',
  orders: '/ordenes',
  vouchers: '/vales',
  attendances: '/atenciones',
  reports: '/reportes',
  fuelTypes: '/combustibles',
  users: '/usuarios',
} as const;

export const SESSION_EXPIRED_REASON = 'session_expired';

/** Orden de presentación de roles (el backend devuelve ADMIN/OFFICE/ATTENDANT). */
export const USER_ROLES: readonly UserRole[] = ['OFFICE', 'ATTENDANT', 'ADMIN'];

export const ROLE_LABELS: Readonly<Record<UserRole, string>> = {
  ADMIN: 'Administrador',
  OFFICE: 'Oficina',
  ATTENDANT: 'Grifero',
};

/** Permisos agrupados por módulo, para construir menús o botones. */
export const PERMISSIONS = {
  usersManage: 'users.manage',
  fuelTypesRead: 'fuel_types.read',
  fuelTypesManage: 'fuel_types.manage',
  ordersRead: 'purchase_orders.read',
  ordersCreate: 'purchase_orders.create',
  ordersUpdate: 'purchase_orders.update',
  ordersDelete: 'purchase_orders.delete',
  vouchersRead: 'vouchers.read',
  vouchersCorrect: 'vouchers.correct_descriptive',
  vouchersDelete: 'vouchers.delete',
  attendancesCreate: 'attendances.create',
  attendancesReadOwn: 'attendances.read_own',
  attendancesReadAll: 'attendances.read_all',
  balancesRead: 'balances.read',
  reportsRead: 'reports.read',
  reportsExport: 'reports.export',
  ocrProcess: 'ocr.purchase_orders.process',
} as const satisfies Readonly<Record<string, Permission>>;

/**
 * Menú completo del panel. Solo incluye vistas reales de `app.routes.ts`:
 * dashboard (`''`), `ordenes`, `vales`, `atenciones`, `reportes` y `usuarios`.
 * Las vistas de detalle no se listan: heredan el rol de su sección.
 */
export const NAV: readonly NavEntry[] = [
  {
    id: 'workspace',
    label: 'Espacio de trabajo',
    children: [
      {
        id: 'dashboard',
        label: 'Panel de control',
        icon: 'dashboard',
        path: `${ADMIN_PREFIX}/`,
        roles: ALL_ROLES,
      },
      {
        id: 'orders',
        label: 'Órdenes de compra',
        icon: 'orders',
        path: `${ADMIN_PREFIX}/ordenes`,
        roles: ALL_ROLES,
      },
      {
        id: 'vouchers',
        label: 'Vales',
        icon: 'vouchers',
        path: `${ADMIN_PREFIX}/vales`,
        roles: ALL_ROLES,
      },
      {
        id: 'attendances',
        label: 'Atenciones',
        icon: 'attendances',
        path: `${ADMIN_PREFIX}/atenciones`,
        roles: ALL_ROLES,
        hiddenFor: ['ADMIN'],
      },
    ],
  },
  {
    id: 'control',
    label: 'Control y administración',
    children: [
      {
        id: 'reports',
        label: 'Reportes',
        icon: 'reports',
        path: `${ADMIN_PREFIX}/reportes`,
        roles: ['ADMIN', 'OFFICE'],
      },
      {
        id: 'fuel-types',
        label: 'Combustibles',
        icon: 'fuel',
        path: `${ADMIN_PREFIX}/combustibles`,
        roles: ['ADMIN'],
      },
      {
        id: 'users',
        label: 'Usuarios',
        icon: 'users',
        path: `${ADMIN_PREFIX}/usuarios`,
        roles: ['ADMIN'],
      },
    ],
  },
];

const isGroup = (entry: NavEntry): entry is NavGroup => 'children' in entry;

const allChildren = (): readonly NavChild[] =>
  NAV.flatMap((entry) => (isGroup(entry) ? entry.children : [entry]));

/** Normaliza una URL para compararla con `NavChild.path` (`/` para la raíz). */
const normalizePath = (url: string): string => {
  const path = url.split('?')[0].split('#')[0].replace(/\/+$/, '');
  return path === '' ? '/' : path;
};

/** Entradas visibles para el rol, descartando grupos vacíos. */
export const navForRole = (role: UserRole | undefined): NavEntry[] => {
  if (!role) {
    return [];
  }
  const visible = (child: NavChild): boolean => child.roles.includes(role) && !child.hiddenFor?.includes(role);
  return NAV.filter(
    (entry): entry is NavGroup =>
      isGroup(entry) && entry.children.some(visible),
  ).map((group) => ({
    ...group,
    children: group.children.filter(visible),
  }));
};

/** Sección de navegación que corresponde a una URL del panel. */
export const navChildForRoute = (route: string): NavChild | undefined => {
  const path = normalizePath(route);
  return allChildren().find((child) => child.path === path);
};

/**
 * Roles autorizados para una ruta. Las rutas desconocidas no se restringen aquí:
 * el guard solo decide sobre las secciones declaradas en `NAV`.
 */
export const rolesForRoute = (route: string): UserRole[] => {
  const child = navChildForRoute(route);
  return child ? [...child.roles] : [...ALL_ROLES];
};

import type { Permission, UserRole } from '../models/auth.model';

/** Rutas de la aplicación (las que ya existen en `app.routes.ts`). */
export const APP_ROUTES = {
  login: '/login',
  dashboard: '/',
  orders: '/ordenes',
  vouchers: '/vales',
  attendances: '/atenciones',
  reports: '/reportes',
  users: '/usuarios',
} as const;

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

/** Agrupación temporal que acepta `GET /reports/dashboard`. */
export const REPORT_GROUPINGS = ['hour', 'day', 'week', 'month'] as const;

/** Tipos de emisor de un vale (`^(INSTITUTION|STATION)$`). */
export const ISSUER_TYPES = ['INSTITUTION', 'STATION'] as const;

export const ISSUER_TYPE_LABELS: Readonly<Record<(typeof ISSUER_TYPES)[number], string>> = {
  INSTITUTION: 'Institución',
  STATION: 'Estación',
};

/** Formatos de exportación de reportes. */
export const REPORT_EXPORT_FORMATS = ['pdf', 'xlsx'] as const;

/** Ordenamientos que acepta `GET /purchase-orders`. */
export const ORDER_SORT_FIELDS = ['issue_date', 'order_number', 'institution_name'] as const;

export const SESSION_EXPIRED_REASON = 'expired';

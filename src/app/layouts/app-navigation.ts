export interface AppNavigationItem {
  readonly label: string;
  readonly path: string;
  readonly permission: string;
}

export const APP_NAVIGATION: readonly AppNavigationItem[] = [
  { label: 'Panel principal', path: '/app/dashboard', permission: 'reports.read' },
  { label: 'Usuarios', path: '/app/users', permission: 'users.manage' },
  { label: 'Órdenes de compra', path: '/app/orders', permission: 'purchase_orders.read' },
  { label: 'Atenciones', path: '/app/attendances', permission: 'attendances.create' },
  { label: 'Vales', path: '/app/vouchers', permission: 'vouchers.read' },
  { label: 'Verificación', path: '/app/verifications', permission: 'vouchers.verify' },
  { label: 'Reportes', path: '/app/reports', permission: 'reports.read' },
];

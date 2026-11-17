export interface NavigationItem {
  readonly label: string;
  readonly path: string;
  readonly permission: string;
}

export interface NavigationGroup {
  readonly label: string;
  readonly items: readonly NavigationItem[];
}

export const NAVIGATION: readonly NavigationGroup[] = [
  { label: 'Inicio', items: [
    { label: 'Panel principal', path: '/app/dashboard', permission: 'reports.read' },
  ] },
  { label: 'Operaciones', items: [
    { label: 'Órdenes de compra', path: '/app/purchase-orders', permission: 'purchase_orders.read' },
    { label: 'Vales', path: '/app/vouchers', permission: 'vouchers.read' },
    { label: 'Espacio de atención', path: '/app/attendant/workspace', permission: 'attendances.create' },
    { label: 'Mis atenciones', path: '/app/attendant/attendances', permission: 'attendances.read_own' },
    { label: 'Atenciones', path: '/app/attendances', permission: 'attendances.read_all' },
    { label: 'Saldos', path: '/app/balances', permission: 'balances.read' },
  ] },
  { label: 'Oficina', items: [
    { label: 'Verificación', path: '/app/attendances/pending-verification', permission: 'vouchers.verify' },
  ] },
  { label: 'Herramientas', items: [
    { label: 'Reportes', path: '/app/reports', permission: 'reports.read' },
  ] },
  { label: 'Administración', items: [
    { label: 'Usuarios', path: '/app/users', permission: 'users.manage' },
  ] },
];

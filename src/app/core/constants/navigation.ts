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
    { label: 'Panel principal', path: '/dashboard', permission: 'reports.read' },
  ] },
  { label: 'Operaciones', items: [
    { label: 'Órdenes de compra', path: '/purchase-orders', permission: 'purchase_orders.read' },
    { label: 'Vales', path: '/vouchers', permission: 'vouchers.read' },
    { label: 'Espacio de atención', path: '/attendant/workspace', permission: 'attendances.create' },
    { label: 'Vales atendidos', path: '/attendant/attendances', permission: 'attendances.read_own' },
    { label: 'Atenciones', path: '/attendances', permission: 'attendances.read_all' },
    { label: 'Saldos', path: '/balances', permission: 'balances.read' },
  ] },
  { label: 'Herramientas', items: [
    { label: 'Reportes', path: '/reports', permission: 'reports.read' },
  ] },
  { label: 'Administración', items: [
    { label: 'Usuarios', path: '/users', permission: 'users.manage' },
  ] },
];

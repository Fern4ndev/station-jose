import type { StatCardModel } from '../../shared/components/ui-stat-card/ui-stat-card';
import {
  DEMO_ORDERS,
  formatGallons,
  matchesBranch,
  orderBalance,
  padCount,
  type DemoOrder,
} from '../orders/orders-data';
import { DEMO_VOUCHERS, voucherBalance, type DemoVoucher } from '../vouchers/vouchers-data';

export type ReportPeriod = '7d' | 'month' | 'year';

export interface ReportBucket {
  readonly label: string;
  readonly sanJose: number;
  readonly santaMarta: number;
}

export interface ReportDataset {
  readonly badge: string;
  readonly buckets: readonly ReportBucket[];
  readonly attendances: { readonly sanJose: number; readonly santaMarta: number };
}

export interface ReportSummary {
  readonly authorized: string;
  readonly dispatched: string;
  readonly balance: string;
  readonly percent: number;
  readonly vouchers: number;
}

export const REPORT_PERIODS: readonly { value: ReportPeriod; label: string }[] = [
  { value: '7d', label: 'Últimos 7 días' },
  { value: 'month', label: 'Este mes' },
  { value: 'year', label: 'Este año' },
];

const series = (
  labels: readonly string[],
  sanJose: readonly number[],
  santaMarta: readonly number[],
): readonly ReportBucket[] =>
  labels.map((label, index) => ({ label, sanJose: sanJose[index], santaMarta: santaMarta[index] }));

export const REPORT_DATASETS: Readonly<Record<ReportPeriod, ReportDataset>> = {
  '7d': {
    badge: 'Últimos 7 días',
    buckets: series(
      ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
      [128.5, 196, 150, 236, 178, 279, 159.5],
      [84, 138.5, 180.5, 162, 217.5, 208, 113],
    ),
    attendances: { sanJose: 48, santaMarta: 38 },
  },
  month: {
    badge: 'Este mes',
    buckets: series(
      ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4'],
      [512, 604.5, 478, 706],
      [388.5, 451, 402.5, 529],
    ),
    attendances: { sanJose: 96, santaMarta: 84 },
  },
  year: {
    badge: 'Este año',
    buckets: series(
      ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic'],
      [1240, 1180, 1410, 1320, 1050, 1480, 1560, 1390, 1610, 1470, 1530, 1120],
      [940, 980, 1090, 1010, 870, 1150, 1210, 1080, 1240, 1160, 1190, 960],
    ),
    attendances: { sanJose: 489, santaMarta: 421 },
  },
};

/** Suma el par de sedes o solo la sede activa. */
const scoped = (
  branch: string,
  values: { readonly sanJose: number; readonly santaMarta: number },
): number => {
  if (branch === 'San José') {
    return values.sanJose;
  }
  return branch === 'Santa Marta' ? values.santaMarta : values.sanJose + values.santaMarta;
};

export const countActiveVouchers = (
  branch: string,
  vouchers: readonly DemoVoucher[] = DEMO_VOUCHERS,
  orders: readonly DemoOrder[] = DEMO_ORDERS,
): number =>
  vouchers.filter((voucher) => {
    const order = orders.find((item) => item.id === voucher.orderId);
    return voucherBalance(voucher) > 0 && order !== undefined && matchesBranch(order.branch, branch);
  }).length;

export function buildReportMetrics(
  dataset: ReportDataset,
  branch: string,
  orders: readonly DemoOrder[] = DEMO_ORDERS,
  vouchers: readonly DemoVoucher[] = DEMO_VOUCHERS,
): readonly StatCardModel[] {
  const gallons = dataset.buckets.reduce((total, bucket) => total + scoped(branch, bucket), 0);
  const attendances = scoped(branch, dataset.attendances);
  const activeOrders = orders.filter(
    (order) => orderBalance(order) > 0 && matchesBranch(order.branch, branch),
  ).length;

  return [
    {
      id: 'gallons',
      label: 'Galones atendidos',
      value: formatGallons(gallons),
      suffix: 'gal',
      note: 'En el período seleccionado',
      icon: 'attendances',
      tone: 'mint',
    },
    {
      id: 'attendances',
      label: 'Atenciones',
      value: padCount(attendances),
      note: branch === 'Todas las sedes' ? 'En ambas sedes' : `En la sede ${branch}`,
      icon: 'reports',
      tone: 'amber',
    },
    {
      id: 'orders',
      label: 'Órdenes activas',
      value: padCount(activeOrders),
      note: 'Con saldo pendiente',
      icon: 'orders',
      tone: 'mint',
    },
    {
      id: 'vouchers',
      label: 'Vales con saldo',
      value: padCount(countActiveVouchers(branch, vouchers, orders)),
      note: 'Pendientes de atender',
      icon: 'vouchers',
      tone: 'amber',
    },
  ];
}

export function buildReportSummary(
  branch: string,
  orders: readonly DemoOrder[] = DEMO_ORDERS,
  vouchers: readonly DemoVoucher[] = DEMO_VOUCHERS,
): ReportSummary {
  const visible = orders.filter((order) => matchesBranch(order.branch, branch));
  const authorized = visible.reduce((total, order) => total + order.total, 0);
  const dispatched = visible.reduce((total, order) => total + order.used, 0);
  const balance = visible.reduce((total, order) => total + orderBalance(order), 0);
  const percent = authorized === 0 ? 0 : Math.round((balance / authorized) * 100);

  return {
    authorized: `${formatGallons(authorized)} gal`,
    dispatched: `${formatGallons(dispatched)} gal`,
    balance: `${formatGallons(balance)} gal`,
    percent,
    vouchers: countActiveVouchers(branch, vouchers, orders),
  };
}

/** Exporta el mismo informe de saldos que muestra la vista, filtrado por sede. */
export function buildReportCsv(
  branch: string,
  orders: readonly DemoOrder[] = DEMO_ORDERS,
): string {
  const rows: readonly (readonly (string | number)[])[] = [
    ['Orden', 'Entidad', 'Sede', 'Combustible', 'Autorizado (gal)', 'Despachado (gal)', 'Saldo (gal)'],
    ...orders
      .filter((order) => matchesBranch(order.branch, branch))
      .map((order) => [
        order.id,
        order.entity,
        order.branch,
        order.fuel,
        order.total,
        order.used,
        orderBalance(order),
      ]),
  ];

  return rows
    .map((row) => row.map((field) => `"${String(field).replace(/"/g, '""')}"`).join(','))
    .join('\r\n');
}

export const reportFileName = (branch: string): string =>
  `reporte-saldos-${branch === 'Todas las sedes' ? 'todas-las-sedes' : branch.toLowerCase().replace(/\s+/g, '-')}.csv`;

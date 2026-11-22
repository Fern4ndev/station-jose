import type { StatCardModel } from '../../shared/components/ui-stat-card/ui-stat-card';
import { DEMO_ATTENDANCES, visibleAttendances } from '../attendances/attendances-data';
import {
  DEMO_ORDERS,
  formatGallons,
  matchesBranch,
  orderBalance,
  padCount,
} from '../orders/orders-data';
import { DEMO_VOUCHERS, voucherBalance } from '../vouchers/vouchers-data';

/**
 * Construye las tres tarjetas del dashboard. `attendant` es el nombre del
 * grifero autenticado; `null` para Oficina y Administración.
 */
export function buildDashboardMetrics(
  attendant: string | null,
  branch: string,
): readonly StatCardModel[] {
  const visible = visibleAttendances(DEMO_ATTENDANCES, attendant, branch);
  const activeOrders = DEMO_ORDERS.filter(
    (order) => orderBalance(order) > 0 && matchesBranch(order.branch, branch),
  ).length;
  const activeVouchers = DEMO_VOUCHERS.filter((voucher) => {
    const order = DEMO_ORDERS.find((candidate) => candidate.id === voucher.orderId);
    return voucherBalance(voucher) > 0 && order !== undefined && matchesBranch(order.branch, branch);
  }).length;
  const gallonsToday = visible.reduce((total, item) => total + item.gallons, 0);

  return [
    {
      id: 'orders',
      label: attendant === null ? 'Órdenes activas' : 'Órdenes disponibles',
      value: padCount(activeOrders),
      note: '· con saldo disponible',
      noteLead: branch === 'Todas las sedes' ? 'En ambas sedes' : branch,
      icon: 'orders',
      tone: 'mint',
    },
    {
      id: 'gallons',
      label: attendant === null ? 'Galones despachados' : 'Mis galones hoy',
      value: formatGallons(gallonsToday),
      suffix: 'gal',
      note: 'Total registrado hoy',
      icon: 'attendances',
      tone: 'mint',
    },
    {
      id: 'vouchers',
      label: 'Vales con saldo',
      value: padCount(activeVouchers),
      note: 'Disponibles o parcialmente atendidos',
      icon: 'vouchers',
      tone: 'amber',
    },
  ];
}

import type { PurchaseOrderCreate, PurchaseOrderDetail } from '../../core/models/purchase-order';

export interface DemoOrder {
  readonly id: string;
  readonly entity: string;
  readonly date: string;
  readonly branch: string;
  readonly fuel: string;
  readonly total: number;
  readonly used: number;
  readonly apiId?: string;
  readonly key?: string;
  readonly source?: PurchaseOrderDetail;
}

export type OrderFilter = 'Todas' | 'Con saldo' | 'Agotadas';

export interface OrderDraft {
  readonly payload: PurchaseOrderCreate;
}

export const orderBalance = (order: DemoOrder): number => Math.max(0, order.total - order.used);

/** Sede activa del armazón: `Todas las sedes` no filtra. */
export const matchesBranch = (branch: string, selected: string): boolean =>
  selected === 'Todas las sedes' || branch === selected;

export const padCount = (value: number): string => String(value).padStart(2, '0');

export const formatGallons = (value: number): string =>
  new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(value);

export const orderPercent = (order: DemoOrder): number =>
  order.total === 0 ? 0 : Math.round((orderBalance(order) / order.total) * 100);

export function filterOrders(
  orders: readonly DemoOrder[],
  filter: OrderFilter,
  query: string,
  branch: string,
): readonly DemoOrder[] {
  const term = query.trim().toLowerCase();
  return orders.filter((order) => {
    const matchesQuery = `${order.id} ${order.entity} ${order.fuel}`.toLowerCase().includes(term);
    const inBranch = matchesBranch(order.branch, branch);
    const balance = orderBalance(order);
    const matchesStatus =
      filter === 'Todas' || (filter === 'Con saldo' && balance > 0) || (filter === 'Agotadas' && balance === 0);
    return matchesQuery && inBranch && matchesStatus;
  });
}

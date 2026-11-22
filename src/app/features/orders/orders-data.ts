export interface DemoOrder {
  readonly id: string;
  readonly entity: string;
  readonly date: string;
  readonly branch: string;
  readonly fuel: string;
  readonly total: number;
  readonly used: number;
}

export type OrderFilter = 'Todas' | 'Con saldo' | 'Agotadas';

export interface OrderDraft {
  readonly id: string;
  readonly entity: string;
  readonly date: string;
  readonly branch: string;
  readonly fuel: string;
  readonly total: number;
}

export const DEMO_ORDERS: readonly DemoOrder[] = [
  { id: 'OC-2026-0048', entity: 'Municipalidad Provincial', date: '14 nov 2026', branch: 'San José', fuel: 'Diésel B5', total: 2400, used: 1680 },
  { id: 'OC-2026-0046', entity: 'Red de Salud Norte', date: '12 nov 2026', branch: 'Santa Marta', fuel: 'Gasohol 90', total: 1800, used: 945 },
  { id: 'OC-2026-0044', entity: 'Gobierno Regional', date: '10 nov 2026', branch: 'San José', fuel: 'Diésel B5', total: 3200, used: 3100 },
  { id: 'OC-2026-0041', entity: 'Unidad de Gestión Educativa', date: '08 nov 2026', branch: 'Santa Marta', fuel: 'Gasohol 90', total: 1200, used: 1200 },
  { id: 'OC-2026-0038', entity: 'Municipalidad Distrital', date: '05 nov 2026', branch: 'San José', fuel: 'Diésel B5', total: 2800, used: 1375 },
  { id: 'OC-2026-0035', entity: 'Red de Salud Norte', date: '02 nov 2026', branch: 'Santa Marta', fuel: 'Diésel B5', total: 1600, used: 1220 },
  { id: 'OC-2026-0031', entity: 'Gobierno Regional', date: '29 oct 2026', branch: 'San José', fuel: 'Gasohol 90', total: 2000, used: 2000 },
];

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

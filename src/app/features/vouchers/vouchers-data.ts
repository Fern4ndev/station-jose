import { DEMO_ORDERS, type DemoOrder } from '../orders/orders-data';

export type VoucherIssuerType = 'INSTITUTION' | 'STATION';

export type VoucherStatus = 'Disponible' | 'Parcial' | 'Agotado';

export type VoucherFilter = 'Todos' | VoucherStatus;

export interface DemoVoucher {
  readonly id: string;
  readonly orderId: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
  readonly fuel: string;
  readonly total: number;
  readonly used: number;
}

export interface VoucherDraft {
  readonly id: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
}

export const DEMO_VOUCHERS: readonly DemoVoucher[] = [
  { id: 'VM-2026-0142', orderId: 'OC-2026-0048', issuer: 'Municipalidad Provincial', issuerType: 'INSTITUTION', fuel: 'Diésel B5', total: 140, used: 95 },
  { id: 'VM-2026-0141', orderId: 'OC-2026-0046', issuer: 'Red de Salud Norte', issuerType: 'INSTITUTION', fuel: 'Gasohol 90', total: 80, used: 80 },
  { id: 'VM-2026-0139', orderId: 'OC-2026-0044', issuer: 'Gobierno Regional', issuerType: 'INSTITUTION', fuel: 'Diésel B5', total: 220, used: 110 },
  { id: 'VM-2026-0137', orderId: 'OC-2026-0038', issuer: 'Municipalidad Distrital', issuerType: 'INSTITUTION', fuel: 'Diésel B5', total: 60, used: 60 },
  { id: 'VM-2026-0135', orderId: 'OC-2026-0035', issuer: 'Red de Salud Norte', issuerType: 'INSTITUTION', fuel: 'Diésel B5', total: 120, used: 40 },
  { id: 'VM-2026-0134', orderId: 'OC-2026-0031', issuer: 'Gobierno Regional', issuerType: 'STATION', fuel: 'Gasohol 90', total: 45, used: 45 },
];

export const voucherBalance = (voucher: DemoVoucher): number => Math.max(0, voucher.total - voucher.used);

export const voucherPercent = (voucher: DemoVoucher): number =>
  voucher.total === 0 ? 0 : Math.round((voucherBalance(voucher) / voucher.total) * 100);

export const voucherStatus = (voucher: DemoVoucher): VoucherStatus => {
  const balance = voucherBalance(voucher);
  if (balance === 0) {
    return 'Agotado';
  }
  return voucher.used === 0 ? 'Disponible' : 'Parcial';
};

export function filterVouchers(
  vouchers: readonly DemoVoucher[],
  filter: VoucherFilter,
  query: string,
  branch: string,
  orders: readonly DemoOrder[] = DEMO_ORDERS,
): readonly DemoVoucher[] {
  const term = query.trim().toLowerCase();
  return vouchers.filter((voucher) => {
    const status = voucherStatus(voucher);
    const matchesStatus = filter === 'Todos' || filter === status;
    const matchesQuery = `${voucher.id} ${voucher.orderId} ${voucher.issuer}`.toLowerCase().includes(term);
    const order = orders.find((item) => item.id === voucher.orderId);
    const matchesBranch = branch === 'Todas las sedes' || order?.branch === branch;
    return matchesStatus && matchesQuery && matchesBranch;
  });
}

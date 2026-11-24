import type { DemoOrder } from '../orders/orders-data';

export type VoucherIssuerType = 'INSTITUTION' | 'STATION';

export type VoucherStatus = 'Disponible' | 'Parcial' | 'Agotado' | 'Bloqueado';

export type VoucherFilter = 'Todos' | VoucherStatus;

export interface DemoVoucher {
  readonly id: string;
  readonly orderId: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
  readonly fuel: string;
  readonly total: number;
  readonly used: number;
  readonly branch?: string;
  readonly backendStatus?: string;
  readonly lines?: readonly { readonly id: string; readonly fuel: string; readonly authorized: number; readonly attended: number; readonly available: number; readonly status: string }[];
}

export interface VoucherDraft {
  readonly id: string;
  readonly issuer: string;
  readonly issuerType: VoucherIssuerType;
}

export const voucherBalance = (voucher: DemoVoucher): number => Math.max(0, voucher.total - voucher.used);

export const voucherPercent = (voucher: DemoVoucher): number =>
  voucher.total === 0 ? 0 : Math.round((voucherBalance(voucher) / voucher.total) * 100);

export const voucherStatus = (voucher: DemoVoucher): VoucherStatus => {
  if (voucher.backendStatus === 'PARTIALLY_BLOCKED' || voucher.backendStatus === 'BLOCKED_BY_ORDER_BALANCE') return 'Bloqueado';
  const balance = voucherBalance(voucher);
  if (balance === 0) {
    return 'Agotado';
  }
  return voucher.used === 0 ? 'Disponible' : 'Parcial';
};

export function filterVouchers<T extends DemoVoucher>(
  vouchers: readonly T[],
  filter: VoucherFilter,
  query: string,
  branch: string,
  orders: readonly DemoOrder[] = [],
): readonly T[] {
  const term = query.trim().toLowerCase();
  return vouchers.filter((voucher) => {
    const status = voucherStatus(voucher);
    const matchesStatus = filter === 'Todos' || filter === status;
    const matchesQuery = `${voucher.id} ${voucher.orderId} ${voucher.issuer}`.toLowerCase().includes(term);
    const order = orders.find((item) => item.id === voucher.orderId);
    const matchesBranch = branch === 'Todas las sedes' || (voucher.branch ?? order?.branch) === branch;
    return matchesStatus && matchesQuery && matchesBranch;
  });
}

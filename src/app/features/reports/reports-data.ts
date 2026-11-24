export type ReportPeriod = '7d' | 'month' | 'year' | 'custom';

export interface ReportBucket {
  readonly label: string;
  readonly sanJose: number;
  readonly santaMarta: number;
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
  { value: 'custom', label: 'Personalizado' },
];

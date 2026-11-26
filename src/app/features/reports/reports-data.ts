import type { AttendanceReportRow, ReportGrouping } from '../../core/services/reports-api';

export type ReportView = 'day' | 'week' | 'month' | 'year';

export interface ReportSelection {
  readonly kind: 'orders' | 'attendances';
  readonly view: ReportView;
  readonly from: string;
  readonly to: string;
  readonly hourFrom: number;
  readonly hourTo: number;
  readonly branch: string;
}

export const REPORT_VIEWS: readonly { value: ReportView; label: string; detail: string }[] = [
  { value: 'day', label: 'Día', detail: '24 horas' },
  { value: 'week', label: 'Semana', detail: 'Lun–vie' },
  { value: 'month', label: 'Mes', detail: 'Por semanas' },
  { value: 'year', label: 'Año', detail: 'Por meses' },
];

export const REPORT_GROUPING: Readonly<Record<ReportView, ReportGrouping>> = {
  day: 'hour', week: 'day', month: 'week', year: 'month',
};

export interface ReportBucket {
  readonly key?: string;
  readonly label: string;
  readonly detail?: string;
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

const limaDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', hourCycle: 'h23',
});
const dateLabel = new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const monthLabel = new Intl.DateTimeFormat('es-PE', { month: 'short', timeZone: 'UTC' });
const monthDetail = new Intl.DateTimeFormat('es-PE', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const dateOf = (value: string): Date => new Date(`${value}T12:00:00Z`);
const iso = (value: Date): string => value.toISOString().slice(0, 10);

export function reportLocalTime(value: string): { date: string; hour: number } | null {
  const date = new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}-05:00`);
  if (Number.isNaN(date.getTime())) return null;
  const parts = limaDate.formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes): string => parts.find((item) => item.type === type)?.value ?? '';
  return { date: `${part('year')}-${part('month')}-${part('day')}`, hour: Number(part('hour')) };
}

function mondayOf(date: Date): Date {
  const monday = new Date(date);
  monday.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7);
  return monday;
}

export function defaultReportRange(view: ReportView, anchor: Date): { from: Date; to: Date } {
  const from = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());
  const to = new Date(from);
  if (view === 'week') {
    from.setDate(from.getDate() - (from.getDay() + 6) % 7);
    if (to.getDay() === 0) to.setDate(to.getDate() - 2);
    else if (to.getDay() === 6) to.setDate(to.getDate() - 1);
  } else if (view === 'month') from.setDate(1);
  else if (view === 'year') from.setMonth(0, 1);
  return { from, to };
}

export function filterReportAttendances(
  rows: readonly AttendanceReportRow[], selection: ReportSelection,
): readonly AttendanceReportRow[] {
  return rows.filter((row) => {
    const local = reportLocalTime(row.attended_at);
    return local !== null && local.date >= selection.from && local.date <= selection.to
      && local.hour >= selection.hourFrom && local.hour <= selection.hourTo;
  });
}

/** Ejes completos: las franjas sin despachos se conservan con valor cero. */
export function buildReportBuckets(
  rows: readonly AttendanceReportRow[], selection: ReportSelection,
): readonly ReportBucket[] {
  const buckets = new Map<string, { key: string; label: string; detail: string; sanJose: number; santaMarta: number }>();
  const add = (key: string, label: string, detail = label): void => {
    buckets.set(key, { key, label, detail, sanJose: 0, santaMarta: 0 });
  };
  if (selection.view === 'day') {
    for (let hour = 0; hour < 24; hour++) {
      const label = String(hour).padStart(2, '0');
      add(String(hour), label, `${label}:00 – ${label}:59`);
    }
  } else if (selection.view === 'week') {
    ['lun', 'mar', 'mié', 'jue', 'vie'].forEach((day, index) => add(String(index + 1), day));
  } else if (selection.view === 'month') {
    const cursor = mondayOf(dateOf(selection.from));
    let number = 1;
    while (iso(cursor) <= selection.to) {
      const end = new Date(cursor);
      end.setUTCDate(end.getUTCDate() + 6);
      const startLabel = dateLabel.format(dateOf(iso(cursor) < selection.from ? selection.from : iso(cursor)));
      const endLabel = dateLabel.format(dateOf(iso(end) > selection.to ? selection.to : iso(end)));
      add(iso(cursor), `Sem. ${number++}`, `${startLabel} – ${endLabel}`);
      cursor.setUTCDate(cursor.getUTCDate() + 7);
    }
  } else {
    const cursor = dateOf(`${selection.from.slice(0, 7)}-01`);
    while (iso(cursor).slice(0, 7) <= selection.to.slice(0, 7)) {
      add(iso(cursor).slice(0, 7), monthLabel.format(cursor).replace(/\.$/, '').toLowerCase(), monthDetail.format(cursor));
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }
  }
  for (const row of filterReportAttendances(rows, selection)) {
    const local = reportLocalTime(row.attended_at);
    if (!local) continue;
    const date = dateOf(local.date);
    const key = selection.view === 'day' ? String(local.hour)
      : selection.view === 'week' ? String(date.getUTCDay())
      : selection.view === 'month' ? iso(mondayOf(date)) : local.date.slice(0, 7);
    const bucket = buckets.get(key);
    if (!bucket) continue;
    if (row.branch_name === 'San José') bucket.sanJose += Number(row.attended_gallons);
    else if (row.branch_name === 'Santa Marta') bucket.santaMarta += Number(row.attended_gallons);
  }
  return [...buckets.values()];
}

import { ChangeDetectionStrategy, Component, computed, effect, inject, linkedSignal, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { DatePickerModule } from 'primeng/datepicker';
import { TablePagination } from '../../shared/components/table-pagination/table-pagination';
import { MessageService } from 'primeng/api';
import { firstValueFrom } from 'rxjs';
import { CatalogApi } from '../../core/services/catalog-api';
import { ReportsApi, type AttendanceReportRow, type DashboardResponse, type PurchaseOrderReportRow } from '../../core/services/reports-api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { downloadBlob } from '../../shared/utils/download';
import { extractApiError } from '../../shared/utils/api-error';
import { todayIso } from '../../shared/utils/date-range';
import { formatGallons } from '../orders/orders-data';
import type { StatCardModel } from '../../shared/components/ui-stat-card/ui-stat-card';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { TableRefresh } from '../../shared/components/table-refresh/table-refresh';
import { ReportChart } from './components/report-chart/report-chart';
import { ReportMetrics } from './components/report-metrics/report-metrics';
import { ReportSummaryPanel } from './components/report-summary/report-summary';
import {
  REPORT_PERIODS,
  type ReportBucket,
  type ReportSummary,
  type ReportPeriod,
} from './reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, SelectModule, DatePickerModule, TablePagination, ReportChart, ReportMetrics, ReportSummaryPanel, TableRefresh, UiIcon, UiPageHeading],
  selector: 'app-reports',
  templateUrl: './reports.html',
})
export class Reports {
  private loadVersion = 0;
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly api = inject(ReportsApi);
  private readonly catalog = inject(CatalogApi);

  protected readonly periods = [...REPORT_PERIODS];
  protected readonly period = signal<ReportPeriod>('7d');
  protected readonly kind = signal<'orders' | 'attendances'>('orders');
  protected readonly kinds = [{ value: 'orders', label: 'Órdenes' }, { value: 'attendances', label: 'Atenciones' }];
  protected readonly groupings = [{ value: 'hour', label: 'Por hora' }, { value: 'day', label: 'Por día' }, { value: 'week', label: 'Por semana' }, { value: 'month', label: 'Por mes' }];
  protected readonly grouping = signal<'hour' | 'day' | 'week' | 'month'>('day');
  protected readonly today = new Date();
  protected readonly from = signal(this.startOfPeriod('7d'));
  protected readonly to = signal(new Date());
  protected readonly hourOptions = Array.from({ length: 24 }, (_, hour) => ({
    value: hour,
    label: `${String(hour).padStart(2, '0')}:00`,
  }));
  protected readonly hourFrom = signal(0);
  protected readonly hourTo = signal(23);
  protected readonly branch = this.state.branch;

  protected readonly dashboard = signal<DashboardResponse | null>(null);
  protected readonly orderRows = signal<readonly PurchaseOrderReportRow[]>([]);
  protected readonly attendanceRows = signal<readonly AttendanceReportRow[]>([]);
  protected readonly first = linkedSignal({
    source: () => [this.kind(), this.from(), this.to(), this.hourFrom(), this.hourTo(), this.branch(), this.orderRows(), this.attendanceRows()] as const,
    computation: () => 0,
  });
  protected readonly pageSize = signal(10);
  protected readonly filteredAttendanceRows = computed(() => {
    const from = this.hourFrom();
    const to = this.hourTo();
    if (from === 0 && to === 23) return this.attendanceRows();
    return this.attendanceRows().filter((row) => {
      const hour = this.hourOf(row.attended_at);
      return hour !== null && hour >= from && hour <= to;
    });
  });
  /** El servidor entrega lo más reciente primero: el último registro es la fila 1. */
  protected readonly orderedOrderRows = computed(() => this.orderRows());
  protected readonly orderedAttendanceRows = computed(() => this.filteredAttendanceRows());
  protected readonly pagedOrderRows = computed(() => this.orderedOrderRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly pagedAttendanceRows = computed(() => this.orderedAttendanceRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly reportRowCount = computed(() => this.kind() === 'orders' ? this.orderRows().length : this.filteredAttendanceRows().length);

  /** Correlativo estable entre páginas; 1 es el registro más reciente. */
  protected reportRowNumber(index: number): number {
    return this.first() + index + 1;
  }
  protected readonly refreshing = signal(false);
  protected readonly buckets = signal<readonly ReportBucket[]>([]);
  protected readonly visibleBuckets = computed(() => {
    const from = this.hourFrom();
    const to = this.hourTo();
    if (this.grouping() !== 'hour' || (from === 0 && to === 23)) return this.buckets();
    return this.buckets().filter((bucket) => {
      const hour = this.hourOf(bucket.label);
      return hour !== null && hour >= from && hour <= to;
    });
  });
  protected readonly badge = computed(() => this.periods.find((item) => item.value === this.period())?.label ?? '');
  protected readonly metrics = computed<readonly StatCardModel[]>(() => {
    const data = this.dashboard();
    return [
      { id: 'gallons', label: 'Galones atendidos', value: formatGallons(Number(data?.attended_gallons ?? 0)), suffix: 'gal', note: 'En el período seleccionado', icon: 'attendances', tone: 'mint' },
      { id: 'attendances', label: 'Atenciones', value: String(data?.attendances ?? 0), note: 'En el período seleccionado', icon: 'reports', tone: 'amber' },
      { id: 'orders', label: 'Órdenes', value: String(data?.orders ?? 0), note: 'En el período seleccionado', icon: 'orders', tone: 'mint' },
      { id: 'vouchers', label: 'Vales atendidos', value: String(data?.vouchers ?? 0), note: 'En el período seleccionado', icon: 'vouchers', tone: 'amber' },
    ];
  });
  protected readonly summary = computed<ReportSummary>(() => {
    const data = this.dashboard();
    const authorized = Number(data?.authorized_gallons ?? 0);
    const balance = Number(data?.available_gallons ?? 0);
    return {
      authorized: `${formatGallons(authorized)} gal`,
      dispatched: `${formatGallons(Number(data?.attended_gallons ?? 0))} gal`,
      balance: `${formatGallons(balance)} gal`,
      percent: authorized ? Math.round(balance / authorized * 100) : 0,
      vouchers: data?.vouchers ?? 0,
    };
  });

  constructor() {
    effect(() => {
      this.branch();
      this.from();
      this.to();
      this.grouping();
      void this.load();
    });
  }

  private startOfPeriod(period: ReportPeriod): Date {
    const now = new Date();
    const from = new Date(now);
    if (period === '7d') from.setDate(now.getDate() - 6);
    else if (period === 'month') from.setDate(1);
    else if (period === 'year') from.setMonth(0, 1);
    return from;
  }

  private hourOf(value: string): number | null {
    const match = /[T ](\d{2}):/.exec(value);
    return match ? Number(match[1]) : null;
  }

  private filters(): { date_from: string; date_to: string; group_by: 'hour' | 'day' | 'week' | 'month' } {
    return { date_from: todayIso(this.from()), date_to: todayIso(this.to()), group_by: this.grouping() };
  }

  private async load(): Promise<void> {
    const version = ++this.loadVersion;
    this.refreshing.set(true);
    try {
      const filters = this.filters();
      const branches = await firstValueFrom(this.catalog.branches());
      const selected = branches.find((item) => item.name === this.branch());
      const visible = selected ? [selected] : branches;
      const [summary, orderReport, attendanceReport, ...series] = await Promise.all([
        firstValueFrom(this.api.dashboard({ ...filters, branch_id: selected?.id })),
        firstValueFrom(this.api.purchaseOrders({ date_from: filters.date_from, date_to: filters.date_to, branch_id: selected?.id })),
        firstValueFrom(this.api.attendances({ date_from: filters.date_from, date_to: filters.date_to, branch_id: selected?.id })),
        ...visible.map((branch) => firstValueFrom(this.api.dashboard({ ...filters, branch_id: branch.id }))),
      ]);
      if (version !== this.loadVersion) return;
      this.dashboard.set(summary);
      this.orderRows.set(orderReport.items);
      this.attendanceRows.set(attendanceReport.items);
      const periods = new Set(series.flatMap((item) => item.by_period.map((row) => row.period)));
      this.buckets.set([...periods].sort().map((period) => ({
        label: period,
        sanJose: Number(series[visible.findIndex((item) => item.name === 'San José')]?.by_period.find((item) => item.period === period)?.attended_gallons ?? 0),
        santaMarta: Number(series[visible.findIndex((item) => item.name === 'Santa Marta')]?.by_period.find((item) => item.period === period)?.attended_gallons ?? 0),
      })));
    } catch (error) {
      if (version === this.loadVersion) this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudieron cargar los reportes.'), life: 4000 });
    } finally {
      if (version === this.loadVersion) this.refreshing.set(false);
    }
  }

  protected async refresh(): Promise<void> {
    if (this.refreshing()) return;
    this.refreshing.set(true);
    try {
      const { date_from, date_to } = this.filters();
      const branches = await firstValueFrom(this.catalog.branches());
      const branch_id = branches.find((item) => item.name === this.branch())?.id;
      if (this.kind() === 'orders') {
        const report = await firstValueFrom(this.api.purchaseOrders({ date_from, date_to, branch_id }));
        this.orderRows.set(report.items);
      } else {
        const report = await firstValueFrom(this.api.attendances({ date_from, date_to, branch_id }));
        this.attendanceRows.set(report.items);
      }
    } catch (error) {
      this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudo actualizar la tabla.'), life: 4000 });
    } finally {
      this.refreshing.set(false);
    }
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  protected onPeriod(value: ReportPeriod): void {
    this.period.set(value);
    if (value === 'custom') return;
    this.from.set(this.startOfPeriod(value));
    this.to.set(new Date());
    this.grouping.set(value === 'year' ? 'month' : value === 'month' ? 'week' : 'day');
  }

  protected onFrom(value: Date | null): void {
    if (!value) return;
    this.period.set('custom');
    this.from.set(value);
    if (value > this.to()) this.to.set(value);
  }

  protected onTo(value: Date | null): void {
    if (!value) return;
    this.period.set('custom');
    this.to.set(value);
    if (value < this.from()) this.from.set(value);
  }

  protected onHourFrom(value: number): void {
    this.hourFrom.set(value);
    if (value > this.hourTo()) this.hourTo.set(value);
  }

  protected onHourTo(value: number): void {
    this.hourTo.set(value);
    if (value < this.hourFrom()) this.hourFrom.set(value);
  }

  protected resetHours(): void {
    this.hourFrom.set(0);
    this.hourTo.set(23);
  }

  protected exportReport(format: 'pdf' | 'xlsx'): void {
    const { date_from, date_to } = this.filters();
    const branch = this.state.branches().find((item) => item === this.branch());
    void firstValueFrom(this.catalog.branches()).then((branches) => {
      const branch_id = branches.find((item) => item.name === branch)?.id;
      return this.kind() === 'orders'
        ? firstValueFrom(this.api.exportPurchaseOrders(format, { date_from, date_to, branch_id }))
        : firstValueFrom(this.api.exportAttendances(format, { date_from, date_to, branch_id }));
    }).then((blob) => {
      downloadBlob(blob, `reporte-${this.kind() === 'orders' ? 'ordenes' : 'atenciones'}.${format}`);
    }).catch((error: unknown) => {
      this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 });
    });
  }
}

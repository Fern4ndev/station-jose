import { ChangeDetectionStrategy, Component, computed, effect, inject, linkedSignal, signal } from '@angular/core';
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
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
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
  imports: [TablePagination, ReportChart, ReportMetrics, ReportSummaryPanel, TableRefresh, UiIcon, UiPageHeading, UiToast],
  selector: 'app-reports',
  templateUrl: './reports.html',
})
export class Reports {
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly api = inject(ReportsApi);
  private readonly catalog = inject(CatalogApi);

  protected readonly periods = REPORT_PERIODS;
  protected readonly period = signal<ReportPeriod>('7d');
  protected readonly kind = signal<'orders' | 'attendances'>('orders');
  protected readonly branch = this.state.branch;

  protected readonly dashboard = signal<DashboardResponse | null>(null);
  protected readonly orderRows = signal<readonly PurchaseOrderReportRow[]>([]);
  protected readonly attendanceRows = signal<readonly AttendanceReportRow[]>([]);
  protected readonly first = linkedSignal({
    source: () => [this.kind(), this.period(), this.branch(), this.orderRows(), this.attendanceRows()] as const,
    computation: () => 0,
  });
  protected readonly pageSize = signal(10);
  protected readonly pagedOrderRows = computed(() => this.orderRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly pagedAttendanceRows = computed(() => this.attendanceRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly reportRowCount = computed(() => this.kind() === 'orders' ? this.orderRows().length : this.attendanceRows().length);
  protected readonly refreshing = signal(false);
  protected readonly buckets = signal<readonly ReportBucket[]>([]);
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
      this.period();
      void this.load();
    });
  }

  private filters(): { date_from: string; date_to: string; group_by: 'day' | 'week' | 'month' } {
    const now = new Date();
    const from = new Date(now);
    const group_by = this.period() === 'year' ? 'month' : this.period() === 'month' ? 'week' : 'day';
    if (this.period() === '7d') from.setDate(now.getDate() - 6);
    else if (this.period() === 'month') from.setDate(1);
    else from.setMonth(0, 1);
    return { date_from: todayIso(from), date_to: todayIso(now), group_by };
  }

  private async load(): Promise<void> {
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
      this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudieron cargar los reportes.'), life: 4000 });
    } finally {
      this.refreshing.set(false);
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

  protected onPeriod(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as ReportPeriod;
    this.period.set(value);
    const label = this.periods.find((option) => option.value === value)?.label ?? value;
    this.messages.add({ severity: 'info', summary: `Período seleccionado: ${label}.`, life: 2600 });
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

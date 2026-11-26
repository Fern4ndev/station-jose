import { ChangeDetectionStrategy, Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
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
  REPORT_VIEWS, REPORT_GROUPING, buildReportBuckets, defaultReportRange, filterReportAttendances,
  type ReportSummary,
  type ReportSelection, type ReportView,
} from './reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, DatePipe, SelectModule, DatePickerModule, TablePagination, ReportChart, ReportMetrics, ReportSummaryPanel, TableRefresh, UiIcon, UiPageHeading],
  selector: 'app-reports',
  templateUrl: './reports.html',
})
export class Reports {
  private loadVersion = 0;
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly api = inject(ReportsApi);
  private readonly catalog = inject(CatalogApi);

  protected readonly kind = signal<'orders' | 'attendances'>('orders');
  protected readonly kinds = [{ value: 'orders', label: 'Órdenes' }, { value: 'attendances', label: 'Atenciones' }];
  protected readonly views = [...REPORT_VIEWS];
  protected readonly view = signal<ReportView>('week');
  protected readonly today = new Date();
  protected readonly from = signal(defaultReportRange('week', this.today).from);
  protected readonly to = signal(defaultReportRange('week', this.today).to);
  protected readonly hourOptions = Array.from({ length: 24 }, (_, hour) => ({
    value: hour,
    label: `${String(hour).padStart(2, '0')}:00`,
  }));
  protected readonly hourFrom = signal(0);
  protected readonly hourTo = signal(23);
  protected readonly branch = this.state.branch;
  protected readonly applied = signal<ReportSelection>(this.selection());
  protected readonly activeKind = computed(() => this.applied().kind);
  protected readonly hasPending = computed(() => JSON.stringify(this.selection()) !== JSON.stringify(this.applied()));

  protected readonly dashboard = signal<DashboardResponse | null>(null);
  protected readonly orderRows = signal<readonly PurchaseOrderReportRow[]>([]);
  protected readonly attendanceRows = signal<readonly AttendanceReportRow[]>([]);
  protected readonly first = linkedSignal({
    source: () => [this.applied(), this.orderRows(), this.attendanceRows()] as const,
    computation: () => 0,
  });
  protected readonly pageSize = signal(10);
  protected readonly filteredAttendanceRows = computed(() => filterReportAttendances(this.attendanceRows(), this.applied()));
  /** El servidor entrega lo más reciente primero: el último registro es la fila 1. */
  protected readonly orderedOrderRows = computed(() => this.orderRows());
  protected readonly orderedAttendanceRows = computed(() => this.filteredAttendanceRows());
  protected readonly pagedOrderRows = computed(() => this.orderedOrderRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly pagedAttendanceRows = computed(() => this.orderedAttendanceRows().slice(this.first(), this.first() + this.pageSize()));
  protected readonly reportRowCount = computed(() => this.activeKind() === 'orders' ? this.orderRows().length : this.filteredAttendanceRows().length);

  /** Correlativo estable entre páginas; 1 es el registro más reciente. */
  protected reportRowNumber(index: number): number {
    return this.first() + index + 1;
  }
  protected readonly refreshing = signal(false);
  protected readonly visibleBuckets = computed(() => buildReportBuckets(this.attendanceRows(), this.applied()));
  protected readonly badge = computed(() => {
    const format = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' });
    const { from, to } = this.applied();
    return from === to ? format(from) : `${format(from)} – ${format(to)}`;
  });
  protected readonly chartDescription = computed(() => ({
    day: 'Por hora', week: 'Lun–vie', month: 'Por semana', year: 'Por mes',
  })[this.applied().view]);
  protected readonly metrics = computed<readonly StatCardModel[]>(() => {
    const data = this.dashboard();
    return [
      { id: 'gallons', label: 'Galones atendidos', value: formatGallons(Number(data?.attended_gallons ?? 0)), suffix: 'gal', note: 'En el rango aplicado', icon: 'attendances', tone: 'mint' },
      { id: 'attendances', label: 'Atenciones', value: String(data?.attendances ?? 0), note: 'En el rango aplicado', icon: 'reports', tone: 'amber' },
      { id: 'orders', label: 'Órdenes', value: String(data?.orders ?? 0), note: 'En el rango aplicado', icon: 'orders', tone: 'mint' },
      { id: 'vouchers', label: 'Vales atendidos', value: String(data?.vouchers ?? 0), note: 'En el rango aplicado', icon: 'vouchers', tone: 'amber' },
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
    void this.load(this.applied());
  }

  private selection(): ReportSelection {
    return { kind: this.kind(), view: this.view(), from: todayIso(this.from()), to: todayIso(this.to()),
      hourFrom: this.hourFrom(), hourTo: this.hourTo(), branch: this.branch() };
  }

  private async load(selection: ReportSelection): Promise<void> {
    const version = ++this.loadVersion;
    this.refreshing.set(true);
    try {
      const branches = await firstValueFrom(this.catalog.branches());
      const selected = branches.find((item) => item.name === selection.branch);
      const filters = { date_from: selection.from, date_to: selection.to, branch_id: selected?.id };
      const attendanceFilters = { ...filters, hour_from: selection.hourFrom, hour_to: selection.hourTo };
      const [summary, orderReport, attendanceReport] = await Promise.all([
        firstValueFrom(this.api.dashboard({ ...attendanceFilters, group_by: REPORT_GROUPING[selection.view] })),
        firstValueFrom(this.api.purchaseOrders(filters)),
        firstValueFrom(this.api.attendances(attendanceFilters)),
      ]);
      if (version !== this.loadVersion) return;
      this.dashboard.set(summary);
      this.orderRows.set(orderReport.items);
      this.attendanceRows.set(attendanceReport.items);
      this.applied.set(selection);
    } catch (error) {
      if (version === this.loadVersion) this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudieron cargar los reportes.'), life: 4000 });
    } finally {
      if (version === this.loadVersion) this.refreshing.set(false);
    }
  }

  protected async refresh(): Promise<void> {
    if (this.refreshing()) return;
    await this.load(this.applied());
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  protected onView(value: ReportView): void {
    this.view.set(value);
    const range = defaultReportRange(value, this.to());
    this.from.set(range.from);
    this.to.set(range.to);
  }

  protected async applyFilters(event?: Event): Promise<void> {
    event?.preventDefault();
    if (this.refreshing()) return;
    await this.load(this.selection());
  }

  protected onFrom(value: Date | null): void {
    if (!value) return;
    this.from.set(value);
    if (value > this.to()) this.to.set(value);
  }

  protected onTo(value: Date | null): void {
    if (!value) return;
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
    const selection = this.applied();
    const { from: date_from, to: date_to } = selection;
    void firstValueFrom(this.catalog.branches()).then((branches) => {
      const branch_id = branches.find((item) => item.name === selection.branch)?.id;
      return selection.kind === 'orders'
        ? firstValueFrom(this.api.exportPurchaseOrders(format, { date_from, date_to, branch_id }))
        : firstValueFrom(this.api.exportAttendances(format, { date_from, date_to, branch_id, hour_from: selection.hourFrom, hour_to: selection.hourTo }));
    }).then((blob) => {
      downloadBlob(blob, `reporte-${selection.kind === 'orders' ? 'ordenes' : 'atenciones'}.${format}`);
    }).catch((error: unknown) => {
      this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 });
    });
  }
}

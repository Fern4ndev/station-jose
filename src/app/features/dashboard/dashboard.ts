import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { firstValueFrom } from 'rxjs';
import { ReportsApi, type DashboardResponse } from '../../core/services/reports-api';
import { CatalogApi } from '../../core/services/catalog-api';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { extractApiError } from '../../shared/utils/api-error';
import type { StatCardModel } from '../../shared/components/ui-stat-card/ui-stat-card';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { OperationsStore } from '../attendances/operations-store';
import { formatGallons, orderBalance } from '../orders/orders-data';
import { voucherBalance } from '../vouchers/vouchers-data';
import { DashboardActivity } from './components/dashboard-activity/dashboard-activity';
import { DashboardMetrics } from './components/dashboard-metrics/dashboard-metrics';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DashboardActivity, DashboardMetrics, UiIcon, UiPageHeading],
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);
  private readonly operations = inject(OperationsStore);
  private readonly reports = inject(ReportsApi);
  private readonly catalog = inject(CatalogApi);
  private readonly messages = inject(MessageService);
  private readonly report = signal<DashboardResponse | null>(null);

  protected readonly role = this.state.role;
  protected readonly firstName = computed(() => this.state.user().name.split(' ')[0]);
  protected readonly today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  protected readonly subtitle = computed(() => this.role() === 'ATTENDANT'
    ? 'Consulta tus órdenes disponibles y registra cada despacho.'
    : 'Actividad registrada en el sistema.');

  protected readonly metrics = computed<readonly StatCardModel[]>(() => {
    const branch = this.role() === 'ATTENDANT' ? 'Todas las sedes' : this.state.branch();
    const visibleOrders = this.operations.orders().filter((order) => branch === 'Todas las sedes' || order.branch === branch);
    const visibleVouchers = this.operations.vouchers().filter((voucher) => branch === 'Todas las sedes' || voucher.branch === branch);
    const activeOrderIds = new Set(visibleOrders.filter((order) => orderBalance(order) > 0).map((order) => order.apiId));
    const activeVoucherIds = new Set(visibleVouchers.filter((voucher) => voucherBalance(voucher) > 0).map((voucher) => voucher.apiId));
    const gallons = this.role() === 'ATTENDANT'
      ? this.operations.attendances().reduce((sum, item) => sum + item.gallons, 0)
      : Number(this.report()?.attended_gallons ?? 0);
    return [
      { id: 'orders', label: 'Órdenes con saldo', value: String(activeOrderIds.size), note: branch, icon: 'orders', tone: 'mint' },
      { id: 'gallons', label: 'Galones despachados', value: formatGallons(gallons), suffix: 'gal', note: 'Total registrado', icon: 'attendances', tone: 'mint' },
      { id: 'vouchers', label: 'Vales con saldo', value: String(activeVoucherIds.size), note: 'Disponibles o parciales', icon: 'vouchers', tone: 'amber' },
    ];
  });
  protected readonly recent = computed(() => this.operations.attendances().filter((item) =>
    this.state.branch() === 'Todas las sedes' || item.branch === this.state.branch()
  ).slice(0, 4));
  protected readonly scope = computed(() => this.state.branch() === 'Todas las sedes' ? 'ambas sedes' : `la sede ${this.state.branch()}`);

  constructor() {
    void this.operations.load().catch((error: unknown) => this.showError(error));
    if (this.role() !== 'ATTENDANT') {
      effect(() => {
        const branch = this.state.branch();
        void firstValueFrom(this.catalog.branches()).then((items) => {
          const branch_id = items.find((item) => item.name === branch)?.id;
          return firstValueFrom(this.reports.dashboard({ branch_id }));
        }).then((data) => this.report.set(data)).catch((error: unknown) => this.showError(error));
      });
    }
  }

  private showError(error: unknown): void {
    this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 });
  }

  protected goReports(): void { void this.router.navigateByUrl('/reportes'); }
  protected goAttendances(): void { void this.router.navigateByUrl('/atenciones'); }
}

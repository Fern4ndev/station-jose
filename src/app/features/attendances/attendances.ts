import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { AuthService } from '../../core/services/auth/auth';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiStatusBadge } from '../../shared/components/ui-status-badge/ui-status-badge';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { extractApiError } from '../../shared/utils/api-error';
import { formatGallons, orderBalance } from '../orders/orders-data';
import { AttendanceFormDialog } from './components/attendance-form-dialog/attendance-form-dialog';
import { AttendanceHistory } from './components/attendance-history/attendance-history';
import { AttendanceRecent } from './components/attendance-recent/attendance-recent';
import { visibleAttendances, type AttendanceRequest } from './attendances-data';
import { OperationsStore } from './operations-store';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    AttendanceFormDialog,
    AttendanceHistory,
    AttendanceRecent,
    UiIcon,
    UiPageHeading,
    UiPanel,
    UiStatusBadge,
    UiToast,
  ],
  selector: 'app-attendances',
  templateUrl: './attendances.html',
})
export class Attendances {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly auth = inject(AuthService);
  private readonly operations = inject(OperationsStore);

  protected readonly attendances = this.operations.attendances;
  protected readonly vouchers = this.operations.vouchers;
  protected readonly orders = this.operations.orders;
  protected readonly resetToken = signal(0);
  protected readonly registerOpen = signal(false);
  protected readonly saving = signal(false);
  protected readonly canRegister = computed(() => this.auth.hasPermission('attendances.create'));

  protected readonly branch = this.state.branch;
  protected readonly branchLocked = computed(() => this.state.role() === 'ATTENDANT');
  protected readonly availableOrders = computed(() =>
    this.orders().filter(
      (order) =>
        orderBalance(order) > 0 &&
        (this.branchLocked() || this.branch() === 'Todas las sedes' || order.branch === this.branch()),
    ),
  );
  protected readonly visible = computed(() =>
    visibleAttendances(
      this.attendances(),
      this.state.role() === 'ATTENDANT' ? this.state.user().name : null,
      this.branch(),
    ),
  );
  protected readonly recent = computed(() => this.visible().slice(0, 4));

  constructor() {
    void this.operations.load().catch((error: unknown) => {
      this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudieron cargar los despachos.'), life: 4000 });
    });
  }

  protected async register(request: AttendanceRequest): Promise<void> {
    if (this.saving()) return;
    this.saving.set(true);
    try {
      await this.operations.register(request);
      this.resetToken.update((token) => token + 1);
      this.registerOpen.set(false);
      this.messages.add({ severity: 'success', summary: `${formatGallons(request.gallons)} gal registrados en la base de datos.`, life: 2800 });
    } catch (error) {
      this.messages.add({ severity: 'error', summary: extractApiError(error, error instanceof Error ? error.message : 'No se pudo registrar el despacho.'), life: 4000 });
    } finally {
      this.saving.set(false);
    }
  }

  protected goVouchers(): void {
    void this.router.navigateByUrl('/vales');
  }
}

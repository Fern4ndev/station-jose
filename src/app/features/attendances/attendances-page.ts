import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiStatusBadge } from '../../shared/components/ui-status-badge/ui-status-badge';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { formatGallons, orderBalance, DEMO_ORDERS, type DemoOrder } from '../orders/orders-data';
import { DEMO_VOUCHERS, type DemoVoucher } from '../vouchers/vouchers-data';
import { AttendanceFormDialog } from './components/attendance-form-dialog/attendance-form-dialog';
import { AttendanceHistory } from './components/attendance-history/attendance-history';
import { AttendanceRecent } from './components/attendance-recent/attendance-recent';
import {
  DEMO_ATTENDANCES,
  registerAttendance,
  visibleAttendances,
  type AttendanceRequest,
  type DemoAttendance,
} from './attendances-data';

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
  selector: 'app-attendances-page',
  templateUrl: './attendances-page.html',
})
export class AttendancesPage {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);

  protected readonly attendances = signal<readonly DemoAttendance[]>([...DEMO_ATTENDANCES]);
  protected readonly vouchers = signal<readonly DemoVoucher[]>([...DEMO_VOUCHERS]);
  protected readonly orders = signal<readonly DemoOrder[]>([...DEMO_ORDERS]);
  protected readonly resetToken = signal(0);
  protected readonly registerOpen = signal(false);

  protected readonly branch = this.state.branch;
  protected readonly branchLocked = computed(() => this.state.role() === 'ATTENDANT');
  protected readonly availableOrders = computed(() =>
    this.orders().filter(
      (order) =>
        orderBalance(order) > 0 &&
        (this.branch() === 'Todas las sedes' || order.branch === this.branch()),
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

  protected register(request: AttendanceRequest): void {
    const result = registerAttendance(
      { attendances: this.attendances(), orders: this.orders(), vouchers: this.vouchers() },
      request,
      this.state.user().name,
    );

    if (!result.ok) {
      this.messages.add({ severity: 'warn', summary: result.message, life: 3200 });
      return;
    }

    this.attendances.set(result.attendances);
    this.orders.set(result.orders);
    this.vouchers.set(result.vouchers);
    this.resetToken.update((token) => token + 1);
    this.registerOpen.set(false);
    this.messages.add({
      severity: 'success',
      summary: `${formatGallons(result.gallons)} gal registrados. La atención quedó registrada.`,
      life: 2800,
    });
  }

  protected goVouchers(): void {
    void this.router.navigateByUrl('/vales');
  }
}

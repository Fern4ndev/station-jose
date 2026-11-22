import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiConfirmDialog } from '../../shared/components/ui-confirm-dialog/ui-confirm-dialog';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { DEMO_ATTENDANCES } from '../attendances/attendances-data';
import { DEMO_ORDERS } from '../orders/orders-data';
import { VoucherDetailDialog } from './components/voucher-detail-dialog/voucher-detail-dialog';
import { VoucherEditDialog } from './components/voucher-edit-dialog/voucher-edit-dialog';
import { VouchersTable } from './components/vouchers-table/vouchers-table';
import { VouchersToolbar } from './components/vouchers-toolbar/vouchers-toolbar';
import {
  DEMO_VOUCHERS,
  filterVouchers,
  type DemoVoucher,
  type VoucherDraft,
  type VoucherFilter,
} from './vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    UiConfirmDialog,
    UiPageHeading,
    UiPanel,
    UiToast,
    VoucherDetailDialog,
    VoucherEditDialog,
    VouchersTable,
    VouchersToolbar,
  ],
  selector: 'app-vouchers-page',
  templateUrl: './vouchers-page.html',
})
export class VouchersPage {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);

  protected readonly vouchers = signal<readonly DemoVoucher[]>([...DEMO_VOUCHERS]);
  protected readonly filter = signal<VoucherFilter>('Todos');
  protected readonly query = signal('');

  protected readonly detailOpen = signal(false);
  protected readonly editOpen = signal(false);
  protected readonly deleteOpen = signal(false);
  protected readonly selected = signal<DemoVoucher | null>(null);

  protected readonly canCorrect = computed(() => this.state.role() === 'ADMIN');
  protected readonly rows = computed(() =>
    filterVouchers(this.vouchers(), this.filter(), this.query(), this.state.branch(), DEMO_ORDERS),
  );
  protected readonly lockedIds = computed(() => DEMO_ATTENDANCES.map((item) => item.voucher));

  protected openDetail(voucher: DemoVoucher): void {
    this.selected.set(voucher);
    this.detailOpen.set(true);
  }

  protected openEdit(voucher: DemoVoucher): void {
    this.selected.set(voucher);
    this.editOpen.set(true);
  }

  protected askDelete(voucher: DemoVoucher): void {
    if (this.lockedIds().includes(voucher.id)) {
      this.messages.add({
        severity: 'warn',
        summary: 'No se puede eliminar un vale con atenciones registradas.',
        life: 2800,
      });
      return;
    }
    this.selected.set(voucher);
    this.deleteOpen.set(true);
  }

  protected confirmDelete(): void {
    const voucher = this.selected();
    if (!voucher) {
      return;
    }
    this.vouchers.update((vouchers) => vouchers.filter((item) => item.id !== voucher.id));
    this.deleteOpen.set(false);
    this.messages.add({ severity: 'success', summary: 'Vale eliminado.', life: 2800 });
  }

  protected correct(draft: VoucherDraft): void {
    this.vouchers.update((vouchers) =>
      vouchers.map((voucher) =>
        voucher.id === draft.id
          ? { ...voucher, issuer: draft.issuer, issuerType: draft.issuerType }
          : voucher,
      ),
    );
    this.messages.add({
      severity: 'success',
      summary: 'Datos descriptivos del vale actualizados.',
      life: 2800,
    });
  }

  protected goOrders(): void {
    void this.router.navigateByUrl('/ordenes');
  }
}

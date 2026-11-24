import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { VouchersApi } from '../../core/services/vouchers-api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { extractApiError } from '../../shared/utils/api-error';
import { OperationsStore, type DispatchVoucher } from '../attendances/operations-store';
import { VoucherDetailDialog } from './components/voucher-detail-dialog/voucher-detail-dialog';
import { VoucherEditDialog } from './components/voucher-edit-dialog/voucher-edit-dialog';
import { VouchersTable } from './components/vouchers-table/vouchers-table';
import { VouchersToolbar } from './components/vouchers-toolbar/vouchers-toolbar';
import {
  filterVouchers,
  type VoucherDraft,
  type VoucherFilter,
} from './vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    UiPageHeading,
    UiPanel,
    UiToast,
    VoucherDetailDialog,
    VoucherEditDialog,
    VouchersTable,
    VouchersToolbar,
  ],
  selector: 'app-vouchers',
  templateUrl: './vouchers.html',
})
export class Vouchers {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);
  private readonly api = inject(VouchersApi);
  private readonly operations = inject(OperationsStore);

  protected readonly vouchers = this.operations.vouchers;
  protected readonly filter = signal<VoucherFilter>('Todos');
  protected readonly query = signal('');

  protected readonly detailOpen = signal(false);
  protected readonly editOpen = signal(false);
  protected readonly selected = signal<DispatchVoucher | null>(null);

  protected readonly canCorrect = computed(() => this.state.role() === 'ADMIN');
  protected readonly rows = computed(() =>
    filterVouchers(this.vouchers(), this.filter(), this.query(), this.state.role() === 'ATTENDANT' ? 'Todas las sedes' : this.state.branch(), this.operations.orders()),
  );
  protected readonly lockedIds = computed(() => this.vouchers().map((item) => item.id));

  constructor() {
    void this.operations.load().catch((error: unknown) => {
      this.messages.add({ severity: 'error', summary: extractApiError(error, 'No se pudieron cargar los vales.'), life: 4000 });
    });
  }

  protected openDetail(voucher: DispatchVoucher): void {
    this.selected.set(voucher);
    this.detailOpen.set(true);
  }

  protected openEdit(voucher: DispatchVoucher): void {
    this.selected.set(voucher);
    this.editOpen.set(true);
  }

  protected askDelete(): void {
    this.messages.add({ severity: 'warn', summary: 'Los vales con despachos registrados no se pueden eliminar.', life: 2800 });
  }

  protected correct(draft: VoucherDraft): void {
    const voucher = this.selected();
    if (!voucher) return;
    this.api.correctDescriptive(voucher.apiId, {
      issuer_name: draft.issuer,
      issuer_type: draft.issuerType,
    }).subscribe({
      next: () => {
        void this.operations.load().then(() => this.messages.add({ severity: 'success', summary: 'Datos del vale actualizados.', life: 2800 })).catch((error: unknown) => this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 }));
      },
      error: (error: unknown) => this.messages.add({ severity: 'error', summary: extractApiError(error), life: 4000 }),
    });
  }

  protected goOrders(): void {
    void this.router.navigateByUrl('/ordenes');
  }
}

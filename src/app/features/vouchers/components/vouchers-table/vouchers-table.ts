import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiStatusBadge, type StatusTone } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import {
  voucherBalance,
  voucherPercent,
  voucherStatus,
  type DemoVoucher,
  type VoucherStatus,
} from '../../vouchers-data';
import type { DispatchVoucher } from '../../../attendances/operations-store';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, UiIcon, UiStatusBadge],
  selector: 'app-vouchers-table',
  templateUrl: './vouchers-table.html',
})
export class VouchersTable {
  readonly rows = input.required<readonly DispatchVoucher[]>();
  readonly canCorrect = input(false);
  readonly lockedVoucherIds = input<readonly string[]>([]);
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  /** El servidor entrega lo más reciente primero: el último vale es la fila 1. */
  protected readonly orderedRows = computed(() => [...this.rows()]);
  protected readonly pageRows = computed(() =>
    this.orderedRows().slice(this.first(), this.first() + this.pageSize()),
  );

  /** Correlativo estable entre páginas; 1 es el registro más reciente. */
  protected rowNumber(index: number): number {
    return this.first() + index + 1;
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  readonly detail = output<DispatchVoucher>();
  readonly edit = output<DispatchVoucher>();
  readonly remove = output<DispatchVoucher>();

  protected served(voucher: DemoVoucher): string {
    return `${formatGallons(voucher.used)} / ${formatGallons(voucher.total)} gal`;
  }

  protected balance(voucher: DemoVoucher): string {
    return `${formatGallons(voucherBalance(voucher))} gal`;
  }

  protected remaining(voucher: DemoVoucher): string {
    return `${voucherPercent(voucher)}% restante`;
  }

  protected status(voucher: DemoVoucher): VoucherStatus {
    return voucherStatus(voucher);
  }

  protected tone(voucher: DemoVoucher): StatusTone {
    return voucherStatus(voucher) === 'Disponible' ? 'green' : 'amber';
  }
}

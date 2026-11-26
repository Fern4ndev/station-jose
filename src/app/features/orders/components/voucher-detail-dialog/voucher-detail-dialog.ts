import { ChangeDetectionStrategy, Component, input, model } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import type { StatusTone } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../orders-data';
import type { VoucherView } from '../order-detail-dialog/order-detail-dialog';
import type { VoucherStatus } from '../../../vouchers/vouchers-data';

/** Detalle compacto de un vale dentro del detalle de la orden de compra. */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, UiStatusBadge],
  selector: 'app-voucher-detail-dialog',
  templateUrl: './voucher-detail-dialog.html',
})
export class VoucherDetailDialog {
  readonly visible = model(false);
  readonly voucher = input<VoucherView | null>(null);

  protected gallons(value: number | string): string {
    return `${formatGallons(Number(value))} gal`;
  }

  protected percent(value: number, total: number): number {
    if (total <= 0) return 0;
    return Math.min(100, Math.max(0, Math.round((value / total) * 100)));
  }

  protected statusTone(status: VoucherStatus): StatusTone {
    if (status === 'Disponible') return 'green';
    if (status === 'Bloqueado') return 'gray';
    return 'amber';
  }

  protected hasBalance(voucher: VoucherView | null): boolean {
    return (voucher?.balance ?? 0) > 0;
  }
}

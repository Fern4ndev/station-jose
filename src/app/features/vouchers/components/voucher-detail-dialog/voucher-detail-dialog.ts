import { ChangeDetectionStrategy, Component, computed, input, model } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { formatGallons } from '../../../orders/orders-data';
import { voucherBalance, voucherStatus, type DemoVoucher } from '../../vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-voucher-detail-dialog',
  templateUrl: './voucher-detail-dialog.html',
})
export class VoucherDetailDialog {
  readonly visible = model(false);
  readonly voucher = input<DemoVoucher | null>(null);

  protected readonly balance = computed(() => {
    const voucher = this.voucher();
    return voucher ? `${formatGallons(voucherBalance(voucher))} gal` : '—';
  });

  protected readonly status = computed(() => {
    const voucher = this.voucher();
    return voucher ? voucherStatus(voucher) : '—';
  });

  protected gallons(value: number | undefined): string {
    return value === undefined ? '—' : `${formatGallons(value)} gal`;
  }
}

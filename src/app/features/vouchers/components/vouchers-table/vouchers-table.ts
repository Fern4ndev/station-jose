import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
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

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon, UiStatusBadge],
  selector: 'app-vouchers-table',
  templateUrl: './vouchers-table.html',
})
export class VouchersTable {
  readonly rows = input.required<readonly DemoVoucher[]>();
  readonly canCorrect = input(false);
  readonly lockedVoucherIds = input<readonly string[]>([]);

  readonly detail = output<DemoVoucher>();
  readonly edit = output<DemoVoucher>();
  readonly remove = output<DemoVoucher>();

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

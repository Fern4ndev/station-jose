import { ChangeDetectionStrategy, Component, computed, input, model } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { formatGallons, orderBalance, type DemoOrder } from '../../orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-order-detail-dialog',
  templateUrl: './order-detail-dialog.html',
})
export class OrderDetailDialog {
  readonly visible = model(false);
  readonly order = input<DemoOrder | null>(null);

  protected readonly balance = computed(() => {
    const order = this.order();
    return order ? `${formatGallons(orderBalance(order))} gal` : '—';
  });

  protected gallons(value: number | undefined): string {
    return value === undefined ? '—' : `${formatGallons(value)} gal`;
  }
}

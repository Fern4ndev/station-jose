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
    return order ? `${formatGallons(order.source?.items.reduce((sum, item) => sum + Number(item.available_gallons), 0) ?? orderBalance(order))} gal` : '—';
  });

  protected gallons(value: number | string | undefined): string {
    return value === undefined ? '—' : `${formatGallons(Number(value))} gal`;
  }
}

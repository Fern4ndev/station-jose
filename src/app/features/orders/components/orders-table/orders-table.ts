import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons, orderBalance, orderPercent, type DemoOrder } from '../../orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon, UiStatusBadge],
  selector: 'app-orders-table',
  templateUrl: './orders-table.html',
})
export class OrdersTable {
  readonly rows = input.required<readonly DemoOrder[]>();
  readonly canManage = input(false);
  readonly lockedOrderIds = input<readonly string[]>([]);

  readonly view = output<DemoOrder>();
  readonly edit = output<DemoOrder>();
  readonly remove = output<DemoOrder>();

  protected balance(order: DemoOrder): string {
    return `${formatGallons(orderBalance(order))} gal`;
  }

  protected percent(order: DemoOrder): string {
    return `${orderPercent(order)}% del total`;
  }

  protected total(order: DemoOrder): string {
    return `${formatGallons(order.total)} gal`;
  }

  protected hasBalance(order: DemoOrder): boolean {
    return orderBalance(order) > 0;
  }
}

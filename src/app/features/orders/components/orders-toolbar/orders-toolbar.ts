import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { OrderFilter } from '../../orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-orders-toolbar',
  templateUrl: './orders-toolbar.html',
})
export class OrdersToolbar {
  readonly filter = input.required<OrderFilter>();
  readonly query = input.required<string>();

  readonly filterChange = output<OrderFilter>();
  readonly queryChange = output<string>();

  protected readonly filters: readonly OrderFilter[] = ['Todas', 'Con saldo', 'Agotadas'];

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }
}

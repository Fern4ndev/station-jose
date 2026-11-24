import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import type { OrderFilter } from '../../orders-data';
import 'iconify-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, SelectModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-orders-toolbar',
  templateUrl: './orders-toolbar.html',
})
export class OrdersToolbar {
  readonly filter = input.required<OrderFilter>();
  readonly query = input.required<string>();

  readonly filterChange = output<OrderFilter>();
  readonly queryChange = output<string>();

  protected readonly filters: OrderFilter[] = ['Todas', 'Con saldo', 'Agotadas'];

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }
}

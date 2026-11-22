import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { VoucherFilter } from '../../vouchers-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-vouchers-toolbar',
  templateUrl: './vouchers-toolbar.html',
})
export class VouchersToolbar {
  readonly filter = input.required<VoucherFilter>();
  readonly query = input.required<string>();

  readonly filterChange = output<VoucherFilter>();
  readonly queryChange = output<string>();

  protected readonly filters: readonly { value: VoucherFilter; label: string }[] = [
    { value: 'Todos', label: 'Todos' },
    { value: 'Disponible', label: 'Disponibles' },
    { value: 'Parcial', label: 'Parciales' },
    { value: 'Agotado', label: 'Agotados' },
  ];

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }
}

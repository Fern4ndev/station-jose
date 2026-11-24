import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import type { VoucherFilter } from '../../vouchers-data';
import 'iconify-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, SelectModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-vouchers-toolbar',
  templateUrl: './vouchers-toolbar.html',
})
export class VouchersToolbar {
  readonly filter = input.required<VoucherFilter>();
  readonly query = input.required<string>();

  readonly filterChange = output<VoucherFilter>();
  readonly queryChange = output<string>();

  protected readonly filters: { value: VoucherFilter; label: string }[] = [
    { value: 'Todos', label: 'Todos' },
    { value: 'Disponible', label: 'Disponibles' },
    { value: 'Parcial', label: 'Parciales' },
    { value: 'Agotado', label: 'Agotados' },
    { value: 'Bloqueado', label: 'Bloqueados' },
  ];

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }
}

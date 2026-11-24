import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import {
  FUEL_STATUS_FILTERS,
  type FuelStatusFilter,
} from '../../fuel-types-data';
import 'iconify-icon';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, SelectModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-fuel-types-toolbar',
  templateUrl: './fuel-types-toolbar.html',
})
export class FuelTypesToolbar {
  readonly total = input.required<number>();
  readonly query = input.required<string>();
  readonly status = input.required<FuelStatusFilter>();

  readonly queryChange = output<string>();
  readonly statusChange = output<FuelStatusFilter>();

  protected readonly filters = [...FUEL_STATUS_FILTERS];

  protected onQuery(event: Event): void {
    this.queryChange.emit((event.target as HTMLInputElement).value);
  }

  protected onStatus(value: FuelStatusFilter): void {
    this.statusChange.emit(value);
  }
}

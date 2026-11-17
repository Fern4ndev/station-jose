import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface FuelTypeOption { readonly id: string; readonly name: string; }
export interface FuelLineDraft {
  readonly id: string;
  readonly fuelTypeId: string;
  readonly authorizedGallons: string;
  readonly unitPrice: string;
  readonly totalAmount: string;
}
export type FuelLineField = 'fuelTypeId' | 'authorizedGallons' | 'unitPrice' | 'totalAmount';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-fuel-line-editor', templateUrl: './fuel-line-editor.html' })
export class FuelLineEditor {
  readonly lines = input.required<readonly FuelLineDraft[]>();
  readonly fuelTypes = input<readonly FuelTypeOption[]>([]);
  readonly editable = input(true);
  readonly lineChange = output<FuelLineDraft>();
  readonly lineRemove = output<string>();
  readonly lineAdd = output<void>();

  protected update(line: FuelLineDraft, field: FuelLineField, event: Event): void {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;
    this.lineChange.emit({ ...line, [field]: target.value });
  }
}

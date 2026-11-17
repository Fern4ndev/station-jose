import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface DateRangeValue { readonly from: string; readonly to: string; }

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-date-range-filter', templateUrl: './date-range-filter.html' })
export class DateRangeFilter {
  readonly from = input('');
  readonly to = input('');
  readonly rangeChange = output<DateRangeValue>();

  protected updateFrom(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLInputElement) this.rangeChange.emit({ from: target.value, to: this.to() });
  }
  protected updateTo(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLInputElement) this.rangeChange.emit({ from: this.from(), to: target.value });
  }
}

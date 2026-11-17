import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { DateRangeFilter } from '../date-range-filter/date-range-filter';
import type { DateRangeValue } from '../date-range-filter/date-range-filter';

export interface ReportFilterValue extends DateRangeValue { readonly status: string; readonly userId: string; }

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [DateRangeFilter], selector: 'app-report-filter-bar', templateUrl: './report-filter-bar.html' })
export class ReportFilterBar {
  readonly filters = input.required<ReportFilterValue>();
  readonly filtersChange = output<ReportFilterValue>();

  protected updateDateRange(range: DateRangeValue): void {
    this.filtersChange.emit({ ...this.filters(), ...range });
  }

  protected updateStatus(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLSelectElement) this.filtersChange.emit({ ...this.filters(), status: target.value });
  }

  protected updateUser(event: Event): void {
    const target = event.target;
    if (target instanceof HTMLInputElement) this.filtersChange.emit({ ...this.filters(), userId: target.value });
  }
}

import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import type { FuelTypeRow } from '../../fuel-types-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, UiIcon, UiStatusBadge],
  selector: 'app-fuel-types-table',
  templateUrl: './fuel-types-table.html',
})
export class FuelTypesTable {
  readonly rows = input.required<readonly FuelTypeRow[]>();
  readonly busyId = input<string | null>(null);

  readonly edit = output<FuelTypeRow>();
  readonly toggle = output<FuelTypeRow>();

  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  protected readonly pageRows = computed(() =>
    this.rows().slice(this.first(), this.first() + this.pageSize()),
  );

  /** Correlativo ascendente, estable entre páginas. */
  protected rowNumber(index: number): number {
    return this.first() + index + 1;
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }
}

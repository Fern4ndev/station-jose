import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import { TableRefresh } from '../../../../shared/components/table-refresh/table-refresh';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../../attendances/attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, TableRefresh, UiIcon, UiPanel],
  selector: 'app-dashboard-activity',
  templateUrl: './dashboard-activity.html',
})
export class DashboardActivity {
  readonly rows = input.required<readonly DemoAttendance[]>();
  readonly scope = input('ambas sedes');
  readonly refreshing = input(false);
  readonly refresh = output<void>();
  readonly viewAll = output<void>();
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  /** Del registro más reciente al más antiguo: el último despacho es la fila 1. */
  protected readonly orderedRows = computed(() =>
    [...this.rows()].sort((a, b) => (b.attendedAt ?? '').localeCompare(a.attendedAt ?? '')),
  );
  protected readonly pageRows = computed(() =>
    this.orderedRows().slice(this.first(), this.first() + this.pageSize()),
  );

  /** Correlativo estable entre páginas; 1 es el registro más reciente. */
  protected rowNumber(index: number): number {
    return this.first() + index + 1;
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  protected gallons(value: number): string {
    return `${formatGallons(value)} gal`;
  }
}

import { ChangeDetectionStrategy, Component, computed, input, linkedSignal, signal } from '@angular/core';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TablePagination, UiStatusBadge],
  selector: 'app-attendance-history',
  templateUrl: './attendance-history.html',
})
export class AttendanceHistory {
  readonly rows = input.required<readonly DemoAttendance[]>();
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  protected readonly pageRows = computed(() => this.rows().slice(this.first(), this.first() + this.pageSize()));

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  protected gallons(row: DemoAttendance): string {
    return `${formatGallons(row.gallons)} gal`;
  }
}

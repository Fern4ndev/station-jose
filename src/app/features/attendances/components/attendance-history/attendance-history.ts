import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  linkedSignal,
  signal,
} from '@angular/core';
import 'iconify-icon';
import { TablePagination } from '../../../../shared/components/table-pagination/table-pagination';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../attendances-data';
import { AttendanceDetailDialog } from '../attendance-detail-dialog/attendance-detail-dialog';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AttendanceDetailDialog, TablePagination],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-attendance-history',
  templateUrl: './attendance-history.html',
})
export class AttendanceHistory {
  readonly rows = input.required<readonly DemoAttendance[]>();
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  /** Del registro más reciente al más antiguo: el último despacho es la fila 1. */
  protected readonly orderedRows = computed(() =>
    [...this.rows()].sort((a, b) => (b.attendedAt ?? '').localeCompare(a.attendedAt ?? '')),
  );
  protected readonly pageRows = computed(() =>
    this.orderedRows().slice(this.first(), this.first() + this.pageSize()),
  );
  protected readonly detailOpen = signal(false);
  protected readonly selected = signal<DemoAttendance | null>(null);

  protected openDetail(row: DemoAttendance): void {
    this.selected.set(row);
    this.detailOpen.set(true);
  }

  /** Correlativo estable entre páginas; 1 es el registro más reciente. */
  protected rowNumber(index: number): number {
    return this.first() + index + 1;
  }

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  protected gallons(row: DemoAttendance): string {
    return `${formatGallons(row.gallons)} gal`;
  }
}

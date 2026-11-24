import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { PaginatorModule } from 'primeng/paginator';

export interface TablePageChange {
  first?: number;
  rows?: number;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PaginatorModule],
  selector: 'app-table-pagination',
  templateUrl: './table-pagination.html',
  host: { class: 'block w-full' },
})
export class TablePagination {
  readonly first = input(0);
  readonly rows = input(10);
  readonly totalRecords = input(0);
  readonly label = input<string | null>(null);
  readonly pageSizes = input<number[]>([10, 25, 50]);
  readonly pageChange = output<TablePageChange>();
}

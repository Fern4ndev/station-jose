import { ChangeDetectionStrategy, Component, computed, contentChildren, input, output } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { TableModule } from 'primeng/table';
import { EmptyState } from '../empty-state/empty-state';
import { ApiError } from '../api-error/api-error';
import { LoadingSkeleton } from '../loading-skeleton/loading-skeleton';
import { ServerPagination } from '../server-pagination/server-pagination';
import { DataTableCellDirective, DataTableCellContext } from './data-table-cell.directive';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ApiError, EmptyState, LoadingSkeleton, NgTemplateOutlet, ServerPagination, TableModule],
  selector: 'app-data-table',
  styleUrl: './data-table.css',
  templateUrl: './data-table.html',
})
export class DataTable {
  readonly state = input<'loading' | 'error' | 'empty' | 'success'>('empty');
  readonly columns = input.required<readonly string[]>();
  readonly rows = input<readonly Readonly<Record<string, unknown>>[]>([]);
  readonly tableRows = computed(() => [...this.rows()]);
  readonly emptyTitle = input('Sin registros para mostrar');
  readonly emptyDescription = input('No se encontraron resultados.');
  readonly errorMessage = input('No se pudo cargar la información.');
  readonly page = input(1);
  readonly pages = input(1);
  readonly pageChange = output<number>();
  readonly retry = output<void>();
  readonly cellTemplates = contentChildren(DataTableCellDirective);
  readonly cellTemplateMap = computed(() => new Map(this.cellTemplates().map((cell) => [cell.column(), cell.template])));

  cellContext(row: Readonly<Record<string, unknown>>, column: string): DataTableCellContext {
    return { $implicit: row, row, column };
  }
}

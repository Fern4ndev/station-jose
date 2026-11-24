import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  contentChildren,
  input,
  linkedSignal,
  signal,
} from '@angular/core';
import { TablePagination } from '../table-pagination/table-pagination';
import type { TableColumn } from '../../../core/models/table-column';
import { DataTableCell } from './data-table-cell.directive';

/**
 * Tabla de datos compartida. Mantiene el marcado exacto del mockup con
 * utilidades Tailwind, recibe las columnas como `TableColumn[]` y permite
 * reemplazar celdas con `<ng-template appDataTableCell="campo">`.
 *
 * El consumidor conserva la paginación/acciones en su propia capa: la tabla
 * solo pinta `rows`, `loading` y el estado vacío.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NgTemplateOutlet, TablePagination],
  selector: 'app-data-table',
  templateUrl: './data-table.html',
})
export class DataTable<T = Record<string, unknown>> {
  readonly columns = input.required<readonly TableColumn[]>();
  readonly rows = input<readonly T[]>([]);
  readonly loading = input(false);
  readonly emptyMessage = input('Sin registros para mostrar.');
  readonly skeletonRows = input(4);
  protected readonly first = linkedSignal({ source: this.rows, computation: () => 0 });
  protected readonly pageSize = signal(10);
  protected readonly pageRows = computed(() => this.rows().slice(this.first(), this.first() + this.pageSize()));

  protected onPage(event: { first?: number; rows?: number }): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
  }

  private readonly cellTemplates = contentChildren(DataTableCell);

  protected readonly skeletons = computed(() =>
    Array.from({ length: Math.max(1, this.skeletonRows()) }, (_, index) => index),
  );
  protected readonly columnCount = computed(() => Math.max(1, this.columns().length));

  protected templateFor(key: string) {
    return this.cellTemplates().find((cell) => cell.key() === key)?.template ?? null;
  }

  protected valueOf(row: T, column: TableColumn): string {
    const value = (row as Record<string, unknown>)[column.key];
    return value === null || value === undefined || value === '' ? '—' : String(value);
  }
}

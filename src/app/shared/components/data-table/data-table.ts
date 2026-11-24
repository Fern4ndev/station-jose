import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  contentChildren,
  input,
} from '@angular/core';
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
  imports: [NgTemplateOutlet],
  selector: 'app-data-table',
  templateUrl: './data-table.html',
})
export class DataTable<T = Record<string, unknown>> {
  readonly columns = input.required<readonly TableColumn[]>();
  readonly rows = input<readonly T[]>([]);
  readonly loading = input(false);
  readonly emptyMessage = input('Sin registros para mostrar.');
  readonly skeletonRows = input(4);

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

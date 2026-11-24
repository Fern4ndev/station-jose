import { Directive, TemplateRef, input } from '@angular/core';

/**
 * Declara una celda a medida para una columna de `app-data-table`.
 *
 * ```html
 * <ng-template appDataTableCell="status" let-row>
 *   <app-ui-status-badge [label]="row.status" />
 * </ng-template>
 * ```
 */
@Directive({
  selector: 'ng-template[appDataTableCell]',
})
export class DataTableCell {
  /** `key` de la `TableColumn` que esta plantilla reemplaza. */
  readonly key = input.required<string>({ alias: 'appDataTableCell' });

  constructor(readonly template: TemplateRef<unknown>) {}
}

import { Directive, input, TemplateRef, inject } from '@angular/core';

export interface DataTableCellContext {
  readonly $implicit: Readonly<Record<string, unknown>>;
  readonly row: Readonly<Record<string, unknown>>;
  readonly column: string;
}

@Directive({ selector: 'ng-template[appDataTableCell]' })
export class DataTableCellDirective {
  readonly column = input.required<string>({ alias: 'appDataTableCell' });
  readonly template = inject<TemplateRef<DataTableCellContext>>(TemplateRef);
}

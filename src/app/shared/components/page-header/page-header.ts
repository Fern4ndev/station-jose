import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Encabezado de vista del mockup: título, subtítulo opcional y una zona de
 * acciones que el consumidor proyecta (`<ng-content />`).
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-page-header',
  templateUrl: './page-header.html',
})
export class PageHeader {
  readonly title = input.required<string>();
  readonly subtitle = input('');
}

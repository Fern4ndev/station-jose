import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Superficie base del mockup (fondo translúcido, borde suave y sombra corta)
 * sin cabecera: para contenido que no necesita el encabezado de `ui-panel`.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class:
      'block min-w-0 rounded-[18px] border border-(--sanjose-panel-border) bg-(--sanjose-panel) shadow-(--sanjose-panel-shadow) max-[760px]:rounded-[15px]',
  },
  selector: 'app-ui-card',
  template: `
    <section [class]="padded() ? 'p-[16px]' : ''">
      <ng-content />
    </section>
  `,
})
export class UiCard {
  readonly padded = input(true);
}

import { ChangeDetectionStrategy, Component, input, model } from '@angular/core';
import { Dialog } from 'primeng/dialog';

/**
 * Envoltorio de `p-dialog` con la estética del mockup: cabecera con título y
 * descripción, cuerpo proyectado y pie con las acciones del consumidor.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Dialog],
  selector: 'app-ui-dialog',
  templateUrl: './ui-dialog.html',
})
export class UiDialog {
  readonly visible = model(false);
  readonly title = input.required<string>();
  readonly description = input('');
}

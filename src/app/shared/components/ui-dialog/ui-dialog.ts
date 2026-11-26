import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  input,
  model,
} from '@angular/core';
import { Dialog } from 'primeng/dialog';

/**
 * Envoltorio de `p-dialog` con la estética del mockup: cabecera con título y
 * descripción, cuerpo proyectado y pie con las acciones del consumidor.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  // El diálogo se monta en `body`: sus clases deben vivir sin encapsulación.
  encapsulation: ViewEncapsulation.None,
  imports: [Dialog],
  selector: 'app-ui-dialog',
  styleUrl: './ui-dialog.css',
  templateUrl: './ui-dialog.html',
})
export class UiDialog {
  readonly visible = model(false);
  readonly title = input.required<string>();
  readonly description = input('');
  /** Ancho del diálogo; por defecto el del mockup. */
  readonly width = input('min(570px, calc(100vw - 28px))');
}

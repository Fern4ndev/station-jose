import { ChangeDetectionStrategy, Component, input, model, output } from '@angular/core';
import { UiDialog } from '../ui-dialog/ui-dialog';
import { UiButton } from '../ui-button/ui-button';

/**
 * Confirmación de borrado con el diálogo y los botones del sistema visual.
 * El consumidor controla `loading` mientras ejecuta el DELETE real.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiButton, UiDialog],
  selector: 'app-modal-delete',
  templateUrl: './modal-delete.html',
})
export class ModalDelete {
  readonly visible = model(false);
  readonly recordName = input.required<string>();
  readonly title = input('Eliminar registro');
  readonly description = input('Esta acción no se puede deshacer.');
  readonly confirmLabel = input('Eliminar');
  readonly loading = input(false);

  readonly confirmed = output<void>();
}

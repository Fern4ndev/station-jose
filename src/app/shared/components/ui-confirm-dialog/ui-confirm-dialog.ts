import { ChangeDetectionStrategy, Component, input, model, output } from '@angular/core';
import { UiDialog } from '../ui-dialog/ui-dialog';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-ui-confirm-dialog',
  templateUrl: './ui-confirm-dialog.html',
})
export class UiConfirmDialog {
  readonly visible = model(false);
  readonly title = input('Confirmar acción');
  readonly message = input.required<string>();
  readonly confirmLabel = input('Confirmar');
  readonly cancelLabel = input('Cancelar');

  readonly confirmed = output<void>();
}

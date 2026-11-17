import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule, DialogModule],
  selector: 'app-modal-delete',
  templateUrl: './modal-delete.html',
})
export class ModalDelete {
  readonly visible = input(false);
  readonly title = input('Eliminar registro');
  readonly message = input('¿Confirmas que deseas eliminar este registro?');
  readonly visibleChange = output<boolean>();
  readonly confirmed = output<void>();

  confirm(): void {
    this.confirmed.emit();
    this.visibleChange.emit(false);
  }
}

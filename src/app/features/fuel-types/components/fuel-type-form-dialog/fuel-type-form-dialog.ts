import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  model,
  output,
  signal,
} from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { FuelTypeDraft, FuelTypeRow } from '../../fuel-types-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog],
  selector: 'app-fuel-type-form-dialog',
  templateUrl: './fuel-type-form-dialog.html',
})
export class FuelTypeFormDialog {
  readonly visible = model(false);
  readonly editing = input<FuelTypeRow | null>(null);
  readonly saving = input(false);
  readonly error = input('');

  readonly saved = output<FuelTypeDraft>();

  protected readonly name = signal('');
  protected readonly localError = signal('');

  protected readonly isEditing = computed(() => this.editing() !== null);
  protected readonly title = computed(() =>
    this.isEditing() ? 'Editar combustible' : 'Nuevo combustible',
  );
  protected readonly shownError = computed(() => this.localError() || this.error());

  constructor() {
    effect(() => {
      if (!this.visible()) {
        return;
      }
      const current = this.editing();
      this.name.set(current?.name ?? '');
      this.localError.set('');
    });
  }

  protected setName(event: Event): void {
    this.name.set((event.target as HTMLInputElement).value);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const name = this.name().trim();

    if (!name) {
      this.localError.set('Indica el nombre del combustible.');
      return;
    }

    this.localError.set('');
    this.saved.emit({ name });
  }
}

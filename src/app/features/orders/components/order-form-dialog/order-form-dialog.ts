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
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { formatGallons, type DemoOrder, type OrderDraft } from '../../orders-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, UiIcon],
  selector: 'app-order-form-dialog',
  templateUrl: './order-form-dialog.html',
})
export class OrderFormDialog {
  readonly visible = model(false);
  readonly order = input<DemoOrder | null>(null);
  readonly takenIds = input<readonly string[]>([]);

  readonly saved = output<OrderDraft>();

  protected readonly fuels: readonly string[] = ['Diésel B5', 'Gasohol 90'];
  protected readonly branches: readonly string[] = ['San José', 'Santa Marta'];

  protected readonly entity = signal('');
  protected readonly number = signal('');
  protected readonly date = signal('2026-11-15');
  protected readonly fuel = signal('Diésel B5');
  protected readonly total = signal('');
  protected readonly branch = signal('San José');
  protected readonly error = signal('');
  protected readonly pdfLabel = signal('Selecciona un PDF para prellenar los campos');

  protected readonly isEditing = computed(() => this.order() !== null);
  protected readonly title = computed(() =>
    this.isEditing() ? 'Modificar orden' : 'Registrar orden de compra',
  );
  protected readonly description = computed(() =>
    this.isEditing()
      ? 'Actualiza los datos descriptivos sin alterar las atenciones registradas.'
      : 'Completa los datos de la autorización y revisa los galones antes de guardarla.',
  );
  protected readonly usedHint = computed(() => {
    const order = this.order();
    return order ? `Ya se despacharon ${formatGallons(order.used)} gal.` : '';
  });

  constructor() {
    effect(() => {
      if (!this.visible()) {
        return;
      }
      const existing = this.order();
      this.entity.set(existing?.entity ?? '');
      this.number.set(existing?.id ?? '');
      this.date.set('2026-11-15');
      this.fuel.set(existing?.fuel ?? 'Diésel B5');
      this.total.set(existing ? String(existing.total) : '');
      this.branch.set(existing?.branch ?? 'San José');
      this.error.set('');
      this.pdfLabel.set('Selecciona un PDF para prellenar los campos');
    });
  }

  protected setEntity(event: Event): void {
    this.entity.set((event.target as HTMLInputElement).value);
  }

  protected setNumber(event: Event): void {
    this.number.set((event.target as HTMLInputElement).value);
  }

  protected setDate(event: Event): void {
    this.date.set((event.target as HTMLInputElement).value);
  }

  protected setFuel(event: Event): void {
    this.fuel.set((event.target as HTMLSelectElement).value);
  }

  protected setTotal(event: Event): void {
    this.total.set((event.target as HTMLInputElement).value);
  }

  protected setBranch(event: Event): void {
    this.branch.set((event.target as HTMLSelectElement).value);
  }

  protected onPdf(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) {
      return;
    }
    this.pdfLabel.set(`${file.name} · listo para revisar`);
    if (!this.entity().trim()) {
      this.entity.set(file.name.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '));
    }
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const existing = this.order();
    const total = Number(this.total());
    const id = this.number().trim();
    const entity = this.entity().trim();

    if (!entity || !id) {
      this.error.set('Completa la entidad y el número de orden.');
      return;
    }
    if (!Number.isFinite(total) || total <= 0) {
      this.error.set('Indica una cantidad de galones mayor que cero.');
      return;
    }
    if (existing && total < existing.used) {
      this.error.set(`El total no puede ser menor a los ${formatGallons(existing.used)} gal ya despachados.`);
      return;
    }
    if (!existing && this.takenIds().some((taken) => taken.toLowerCase() === id.toLowerCase())) {
      this.error.set('Ese número de orden ya existe.');
      return;
    }

    const date = existing
      ? existing.date
      : new Date(`${this.date()}T12:00:00`)
          .toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
          .replace(/\./g, '');

    this.saved.emit({ id, entity, date, fuel: this.fuel(), total, branch: this.branch() });
    this.visible.set(false);
  }
}

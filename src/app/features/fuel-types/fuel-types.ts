import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { firstValueFrom } from 'rxjs';
import { FuelTypesApi } from '../../core/services/fuel-types-api';
import { extractApiError } from '../../shared/utils/api-error';
import { TableRefresh } from '../../shared/components/table-refresh/table-refresh';
import { UiConfirmDialog } from '../../shared/components/ui-confirm-dialog/ui-confirm-dialog';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiPanel } from '../../shared/components/ui-panel/ui-panel';
import { FuelTypesTable } from './components/fuel-types-table/fuel-types-table';
import { FuelTypesToolbar } from './components/fuel-types-toolbar/fuel-types-toolbar';
import { FuelTypeFormDialog } from './components/fuel-type-form-dialog/fuel-type-form-dialog';
import {
  filterFuelTypes,
  toFuelTypeRow,
  type FuelStatusFilter,
  type FuelTypeDraft,
  type FuelTypeRow,
} from './fuel-types-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    TableRefresh,
    UiConfirmDialog,
    UiIcon,
    UiPageHeading,
    UiPanel,
    FuelTypeFormDialog,
    FuelTypesTable,
    FuelTypesToolbar,
  ],
  selector: 'app-fuel-types',
  templateUrl: './fuel-types.html',
})
export class FuelTypes {
  private readonly messages = inject(MessageService);
  private readonly api = inject(FuelTypesApi);

  protected readonly rows = signal<readonly FuelTypeRow[]>([]);
  protected readonly query = signal('');
  protected readonly status = signal<FuelStatusFilter>('all');
  protected readonly refreshing = signal(false);
  protected readonly saving = signal(false);
  protected readonly formOpen = signal(false);
  protected readonly editing = signal<FuelTypeRow | null>(null);
  protected readonly formError = signal('');
  protected readonly confirmOpen = signal(false);
  protected readonly statusTarget = signal<FuelTypeRow | null>(null);
  protected readonly busyId = signal<string | null>(null);

  protected readonly visibleRows = computed(() =>
    filterFuelTypes(this.rows(), this.query(), this.status()),
  );
  protected readonly confirmMessage = computed(() => {
    const target = this.statusTarget();
    return target
      ? `El combustible ${target.name} dejará de aparecer en el formulario de nuevas órdenes. Las órdenes y reportes existentes no se modifican.`
      : '';
  });

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    this.refreshing.set(true);
    try {
      const fuels = await firstValueFrom(this.api.list({ include_inactive: true }));
      this.rows.set(fuels.map(toFuelTypeRow));
    } catch (error) {
      this.showError(error);
    } finally {
      this.refreshing.set(false);
    }
  }

  protected refresh(): void {
    void this.load();
  }

  protected openNew(): void {
    this.editing.set(null);
    this.formError.set('');
    this.formOpen.set(true);
  }

  protected openEdit(row: FuelTypeRow): void {
    this.editing.set(row);
    this.formError.set('');
    this.formOpen.set(true);
  }

  protected async save(draft: FuelTypeDraft): Promise<void> {
    if (this.saving()) {
      return;
    }
    this.saving.set(true);
    this.formError.set('');
    try {
      const editing = this.editing();
      if (editing) {
        await firstValueFrom(this.api.update(editing.id, { name: draft.name }));
        this.toast('Combustible actualizado.');
      } else {
        await firstValueFrom(this.api.create({ name: draft.name }));
        this.toast('Combustible registrado.');
      }
      this.formOpen.set(false);
      this.editing.set(null);
      await this.load();
    } catch (error) {
      this.formError.set(extractApiError(error, 'No se pudo guardar el combustible.'));
    } finally {
      this.saving.set(false);
    }
  }

  protected requestToggle(row: FuelTypeRow): void {
    if (this.busyId()) {
      return;
    }
    if (row.active) {
      this.statusTarget.set(row);
      this.confirmOpen.set(true);
      return;
    }
    void this.applyStatus(row, true);
  }

  protected confirmToggle(): void {
    const target = this.statusTarget();
    this.confirmOpen.set(false);
    if (target) {
      void this.applyStatus(target, false);
    }
  }

  private async applyStatus(row: FuelTypeRow, isActive: boolean): Promise<void> {
    this.busyId.set(row.id);
    try {
      await firstValueFrom(this.api.setStatus(row.id, { is_active: isActive }));
      this.toast(isActive ? `${row.name} está activo nuevamente.` : `${row.name} fue desactivado.`);
      await this.load();
    } catch (error) {
      this.showError(error);
    } finally {
      this.busyId.set(null);
    }
  }

  private toast(summary: string): void {
    this.messages.add({ severity: 'success', summary, life: 2800 });
  }

  private showError(error: unknown): void {
    this.messages.add({
      severity: 'error',
      summary: extractApiError(error, 'No se pudo completar la operación.'),
      life: 4000,
    });
  }
}

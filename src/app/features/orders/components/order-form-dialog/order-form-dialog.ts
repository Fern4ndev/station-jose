import { ChangeDetectionStrategy, Component, computed, effect, inject, input, model, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { DatePickerModule } from 'primeng/datepicker';
import type { BranchResponse, FuelTypeResponse } from '../../../../core/models/catalog';
import { OcrApi } from '../../../../core/services/ocr-api';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { extractApiError } from '../../../../shared/utils/api-error';
import { todayIso } from '../../../../shared/utils/date-range';
import type { DemoOrder, OrderDraft } from '../../orders-data';

interface DraftLine {
  readonly fuel_type_id: string;
  readonly gallons: string;
  readonly unit_price: string;
}

function lineAmount(gallons: string, price: string): string {
  const scaled = (value: string, places: number): bigint => {
    const [whole, fractional = ''] = value.split('.');
    return BigInt(whole) * 10n ** BigInt(places) + BigInt(fractional.padEnd(places, '0') || '0');
  };
  const cents = (scaled(gallons, 3) * scaled(price, 4) + 50_000n) / 100_000n;
  return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, FormsModule, SelectModule, DatePickerModule],
  selector: 'app-order-form-dialog',
  templateUrl: './order-form-dialog.html',
})
export class OrderFormDialog {
  private readonly ocr = inject(OcrApi);
  readonly visible = model(false);
  readonly order = input<DemoOrder | null>(null);
  readonly takenIds = input<readonly string[]>([]);
  readonly branches = input<readonly BranchResponse[]>([]);
  readonly fuels = input<readonly FuelTypeResponse[]>([]);
  protected readonly branchOptions = computed(() => this.branches().map((item) => ({ value: item.id, label: item.name })));
  protected readonly fuelOptions = computed(() => this.fuels().map((item) => ({ value: item.id, label: item.name })));
  readonly saving = input(false);
  readonly saved = output<OrderDraft>();

  protected readonly title = computed(() => this.order() ? 'Modificar orden' : 'Registrar orden de compra');
  protected readonly number = signal('');
  protected readonly siaf = signal('');
  protected readonly date = signal(todayIso());
  protected readonly dateValue = computed(() => {
    const value = new Date(`${this.date()}T00:00:00`);
    return Number.isNaN(value.getTime()) ? null : value;
  });
  protected readonly supplierDetails = signal('');
  protected readonly executingUnit = signal('');
  protected readonly ruc = signal('');
  protected readonly branch = signal('');
  protected readonly lines = signal<readonly DraftLine[]>([{ fuel_type_id: '', gallons: '', unit_price: '' }]);
  protected readonly error = signal('');
  protected readonly pdfLabel = signal('Selecciona un PDF para prellenar los campos');
  protected readonly loadingOcr = signal(false);

  constructor() {
    effect(() => {
      if (!this.visible()) return;
      const source = this.order()?.source;
      this.number.set(source?.order_number ?? '');
      this.siaf.set(source?.siaf_number ?? '');
      this.date.set(source?.issue_date ?? todayIso());
      this.supplierDetails.set(source?.supplier_details ?? '');
      this.executingUnit.set(source?.executing_unit ?? source?.institution_name ?? '');
      this.ruc.set(source?.executing_unit_ruc ?? '');
      this.branch.set(source?.branch.id ?? '');
      this.lines.set(source?.items.map((item) => ({
        fuel_type_id: item.fuel_type.id,
        gallons: item.authorized_gallons,
        unit_price: 'unit_price' in item ? item.unit_price : '',
      })) ?? [{ fuel_type_id: '', gallons: '', unit_price: '' }]);
      this.error.set('');
      this.pdfLabel.set('Selecciona un PDF para prellenar los campos');
    });
  }

  protected set(field: 'number' | 'siaf' | 'date' | 'supplierDetails' | 'executingUnit' | 'ruc' | 'branch', event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    this[field].set(value);
  }

  protected setLine(index: number, field: keyof DraftLine, event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    this.lines.update((lines) => lines.map((line, at) => at === index ? { ...line, [field]: value } : line));
  }

  protected onDate(value: Date | null): void {
    if (!value) return;
    this.date.set(todayIso(value));
  }

  protected setFuel(index: number, value: string): void {
    this.lines.update((lines) => lines.map((line, at) => at === index ? { ...line, fuel_type_id: value } : line));
  }

  protected addLine(): void {
    this.lines.update((lines) => [...lines, { fuel_type_id: '', gallons: '', unit_price: '' }]);
  }

  protected removeLine(index: number): void {
    if (this.lines().length > 1) this.lines.update((lines) => lines.filter((_, at) => at !== index));
  }

  protected onPdf(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.loadingOcr.set(true);
    this.pdfLabel.set(`Procesando ${file.name}…`);
    this.ocr.analyze(file).subscribe({
      next: (preview) => {
        const fields = preview.fields;
        if (fields.order_number) this.number.set(fields.order_number);
        if (fields.siaf_number) this.siaf.set(fields.siaf_number);
        if (fields.issue_date) this.date.set(fields.issue_date.slice(0, 10));
        if (fields.executing_unit || fields.institution_name) {
          this.executingUnit.set(fields.executing_unit ?? fields.institution_name ?? '');
        }
        if (fields.supplier_name) {
          const supplier = fields.supplier_name.toLocaleLowerCase('es-PE');
          const matchedBranch = this.branches().find((item) =>
            supplier.includes(item.name.toLocaleLowerCase('es-PE')),
          );
          if (matchedBranch) this.branch.set(matchedBranch.id);
        }
        if (fields.executing_unit_ruc) this.ruc.set(fields.executing_unit_ruc);
        if (fields.lines?.length) {
          this.lines.set(fields.lines.map((line) => ({
            fuel_type_id: this.fuels().find((fuel) => line.fuel_description?.toLowerCase().includes(fuel.name.toLowerCase()))?.id ?? '',
            gallons: line.authorized_gallons ?? '',
            unit_price: line.unit_price ?? '',
          })));
        }
        this.pdfLabel.set(`${file.name} · datos sugeridos, revisa todos los campos`);
        this.loadingOcr.set(false);
      },
      error: (error: unknown) => {
        this.error.set(extractApiError(error, 'No se pudo procesar el PDF. Puedes completar la orden manualmente.'));
        this.pdfLabel.set('Selecciona un PDF para prellenar los campos');
        this.loadingOcr.set(false);
      },
    });
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const required = [this.number(), this.siaf(), this.date(), this.executingUnit(), this.ruc(), this.branch()];
    if (required.some((value) => !value.trim())) {
      this.error.set('Completa todos los datos obligatorios de la orden.');
      return;
    }
    const selectedBranch = this.branches().find((item) => item.id === this.branch());
    if (!selectedBranch) {
      this.error.set('Selecciona una sede válida.');
      return;
    }
    if (!this.order() && this.takenIds().some((id) => id.toLowerCase() === this.number().trim().toLowerCase())) {
      this.error.set('Ese número de orden ya existe.');
      return;
    }
    const lines = this.lines();
    if (lines.some((line) => !this.fuels().some((fuel) => fuel.id === line.fuel_type_id)
      || !/^\d+(?:\.\d{1,3})?$/.test(line.gallons) || Number(line.gallons) <= 0
      || !/^\d+(?:\.\d{1,4})?$/.test(line.unit_price))) {
      this.error.set('Cada línea requiere combustible, galones y precio unitario válidos.');
      return;
    }
    if (new Set(lines.map((line) => line.fuel_type_id)).size !== lines.length) {
      this.error.set('No repitas un combustible en la misma orden.');
      return;
    }
    this.saved.emit({ payload: {
      order_number: this.number().trim(),
      siaf_number: this.siaf().trim(),
      issue_date: this.date(),
      institution_name: this.executingUnit().trim(),
      supplier_name: selectedBranch.name,
      supplier_details: this.supplierDetails().trim() || null,
      executing_unit: this.executingUnit().trim(),
      executing_unit_ruc: this.ruc().trim(),
      branch_id: this.branch(),
      items: lines.map((line) => ({
        fuel_type_id: line.fuel_type_id,
        authorized_gallons: line.gallons,
        unit_price: line.unit_price,
        total_amount: lineAmount(line.gallons, line.unit_price),
      })),
    } });
  }
}

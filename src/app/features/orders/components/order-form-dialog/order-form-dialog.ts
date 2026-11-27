import { ChangeDetectionStrategy, Component, computed, effect, input, model, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { DatePickerModule } from 'primeng/datepicker';
import type { BranchResponse, FuelTypeResponse } from '../../../../core/models/catalog';
import type { PurchaseOrderOcrPreview } from '../../../../core/services/ocr-api';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
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
  readonly visible = model(false);
  readonly order = input<DemoOrder | null>(null);
  readonly preview = input<PurchaseOrderOcrPreview | null>(null);
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
  /** Fecha de referencia, refrescada cada vez que se abre el diálogo. */
  private readonly today = signal(todayIso());
  protected readonly dateValue = computed(() => {
    const value = new Date(`${this.date()}T00:00:00`);
    return Number.isNaN(value.getTime()) ? null : value;
  });
  protected readonly supplierDetails = signal('');
  protected readonly institutionName = signal('');
  protected readonly institutionRuc = signal('');
  protected readonly branch = signal('');
  protected readonly lines = signal<readonly DraftLine[]>([{ fuel_type_id: '', gallons: '', unit_price: '' }]);
  protected readonly error = signal('');

  private readonly baseline = computed(() => {
    const source = this.order()?.source;
    const lines: readonly DraftLine[] = source
      ? source.items.map((item) => ({
          fuel_type_id: item.fuel_type.id,
          gallons: item.authorized_gallons,
          unit_price: 'unit_price' in item ? item.unit_price : '',
        }))
      : [{ fuel_type_id: '', gallons: '', unit_price: '' }];
    return {
      number: source?.order_number ?? '',
      siaf: source?.siaf_number ?? '',
      date: source?.issue_date ?? this.today(),
      supplierDetails: source?.supplier_details ?? '',
      institutionName: source?.institution_name ?? source?.executing_unit ?? '',
      institutionRuc: source?.executing_unit_ruc ?? '',
      branch: source?.branch.id ?? '',
      lines,
    };
  });

  /** Solo se puede guardar cuando el formulario difiere de la orden original. */
  protected readonly dirty = computed(() => {
    const base = this.baseline();
    const lines = this.lines();
    return (
      this.number() !== base.number ||
      this.siaf() !== base.siaf ||
      this.date() !== base.date ||
      this.supplierDetails() !== base.supplierDetails ||
      this.institutionName() !== base.institutionName ||
      this.institutionRuc() !== base.institutionRuc ||
      this.branch() !== base.branch ||
      lines.length !== base.lines.length ||
      lines.some((line, index) => {
        const initial = base.lines[index];
        return (
          line.fuel_type_id !== initial.fuel_type_id ||
          line.gallons !== initial.gallons ||
          line.unit_price !== initial.unit_price
        );
      })
    );
  });

  constructor() {
    effect(() => {
      if (!this.visible()) return;
      const source = this.order()?.source;
      this.today.set(todayIso());
      this.number.set(source?.order_number ?? '');
      this.siaf.set(source?.siaf_number ?? '');
      this.date.set(source?.issue_date ?? this.today());
      this.supplierDetails.set(source?.supplier_details ?? '');
      this.institutionName.set(source?.institution_name ?? source?.executing_unit ?? '');
      this.institutionRuc.set(source?.executing_unit_ruc ?? '');
      this.branch.set(source?.branch.id ?? '');
      this.lines.set(source?.items.map((item) => ({
        fuel_type_id: item.fuel_type.id,
        gallons: item.authorized_gallons,
        unit_price: 'unit_price' in item ? item.unit_price : '',
      })) ?? [{ fuel_type_id: '', gallons: '', unit_price: '' }]);
      this.error.set('');
      const preview = this.preview();
      if (preview && !source) this.applyPreview(preview);
    });
  }

  protected set(field: 'number' | 'siaf' | 'date' | 'supplierDetails' | 'institutionName' | 'institutionRuc' | 'branch', event: Event): void {
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

  private applyPreview(preview: PurchaseOrderOcrPreview): void {
    const fields = preview.fields;
    if (fields.order_number) this.number.set(fields.order_number);
    if (fields.siaf_number) this.siaf.set(fields.siaf_number);
    if (fields.issue_date) this.date.set(fields.issue_date.slice(0, 10));
    const extractedName = fields.executing_unit ?? fields.institution_name;
    if (extractedName) this.institutionName.set(extractedName);
    if (fields.executing_unit_ruc) this.institutionRuc.set(fields.executing_unit_ruc);
    if (fields.supplier_name) {
      const supplier = fields.supplier_name.toLocaleLowerCase('es-PE');
      const matchedBranch = this.branches().find((item) =>
        supplier.includes(item.name.toLocaleLowerCase('es-PE')),
      );
      if (matchedBranch) this.branch.set(matchedBranch.id);
    }
    if (fields.lines?.length) {
      this.lines.set(fields.lines.map((line) => ({
        fuel_type_id: this.fuels().find((fuel) => line.fuel_description?.toLowerCase().includes(fuel.name.toLowerCase()))?.id ?? '',
        gallons: line.authorized_gallons ?? '',
        unit_price: line.unit_price ?? '',
      })));
    }
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const required = [this.number(), this.siaf(), this.date(), this.institutionName(), this.institutionRuc(), this.branch()];
    if (required.some((value) => !value.trim())) {
      this.error.set('Completa todos los datos obligatorios de la orden.');
      return;
    }
    const selectedBranch = this.branches().find((item) => item.id === this.branch());
    if (!selectedBranch) {
      this.error.set('Selecciona una sede válida.');
      return;
    }
    if (!/^\d{11}$/.test(this.institutionRuc().trim())) {
      this.error.set('El RUC de la institución debe contener 11 dígitos.');
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
      institution_name: this.institutionName().trim(),
      institution_ruc: this.institutionRuc().trim(),
      supplier_name: selectedBranch.name,
      supplier_details: this.supplierDetails().trim() || null,
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

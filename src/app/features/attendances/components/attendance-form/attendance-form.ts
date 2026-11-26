import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AutoCompleteModule, type AutoCompleteCompleteEvent } from 'primeng/autocomplete';
import { SelectModule } from 'primeng/select';
import { formatGallons } from '../../../orders/orders-data';
import {
  gallonsBalanceMilli,
  gallonsToMilli,
  parseGallonsInput,
} from '../../../../shared/utils/gallons';
import type { VoucherIssuerType } from '../../../vouchers/vouchers-data';
import type { AttendanceLineRequest, AttendanceRequest } from '../../attendances-data';
import type { DispatchOrder, DispatchVoucher } from '../../operations-store';

interface InstitutionOption {
  readonly value: string;
  readonly label: string;
}

/** Línea de combustible que se muestra en el vale. */
interface FuelDraft {
  readonly orderItemId: string;
  readonly voucherItemId?: string;
  readonly fuel: string;
  readonly authorized: string;
  readonly orderAvailableMilli: number;
  readonly voucherAvailableMilli: number | null;
  readonly gallons: string;
}

function normalizeSearch(value: string): string {
  return value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es-PE').trim();
}

function normalizeKey(value: string): string {
  return value.normalize('NFKC').trim().toLocaleLowerCase('es-PE').replace(/\s+/g, ' ');
}

function draftAmount(value: number): string {
  return (gallonsToMilli(value) / 1000).toFixed(3);
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AutoCompleteModule, FormsModule, SelectModule],
  selector: 'app-attendance-form',
  templateUrl: './attendance-form.html',
})
export class AttendanceForm {
  readonly orders = input.required<readonly DispatchOrder[]>();
  readonly vouchers = input.required<readonly DispatchVoucher[]>();
  readonly branch = input('San José');
  readonly branchLocked = input(false);
  readonly resetToken = input(0);

  readonly register = output<AttendanceRequest>();

  protected readonly institutionRuc = signal('');
  protected readonly institutionSuggestions = signal<InstitutionOption[]>([]);
  protected readonly purchaseOrderId = signal('');
  protected readonly voucherId = signal('');
  protected readonly issuer = signal('');
  protected readonly issuerType = signal<VoucherIssuerType>('INSTITUTION');
  protected readonly branchValue = signal('San José');
  protected readonly hint = signal('Vale nuevo: indica los galones autorizados por cada combustible.');
  protected readonly locked = signal(false);
  protected readonly error = signal('');
  protected readonly lines = signal<readonly FuelDraft[]>([]);

  private previousToken = 0;
  private wasLocked = false;
  private linesKey = '';

  protected readonly selectedOrderItems = computed(() =>
    this.orders().filter((order) => order.apiId === this.purchaseOrderId()),
  );

  protected readonly selectedOrder = computed(() => this.selectedOrderItems()[0] ?? null);

  protected readonly institutionOptions = computed(() => {
    const byId = new Map<string, InstitutionOption>();
    for (const order of this.orders()) {
      if (byId.has(order.institutionRuc)) continue;
      byId.set(order.institutionRuc, {
        value: order.institutionRuc,
        label: `${order.entity} · ${order.institutionRuc}`,
      });
    }
    return [...byId.values()]
      .sort((a, b) => a.label.localeCompare(b.label, 'es-PE'))
      .map((item) => ({ value: item.value, label: item.label }));
  });

  protected readonly filteredOrders = computed(() =>
    this.orders().filter((order) => order.institutionRuc === this.institutionRuc()),
  );

  protected readonly orderBalanceLabel = computed(() => {
    const items = this.selectedOrderItems();
    if (!items.length) return '— gal';
    const milli = items.reduce((sum, item) => sum + gallonsBalanceMilli(item.total, item.used), 0);
    return `${formatGallons(milli / 1000)} gal`;
  });

  protected readonly purchaseOrderOptions = computed(() => {
    const byId = new Map<string, DispatchOrder>();
    for (const order of this.filteredOrders()) byId.set(order.apiId, order);
    return [...byId.values()].map((order) => ({
      value: order.apiId,
      label: order.orderNumber,
    }));
  });

  /** Vales con el número escrito que pertenecen a la orden seleccionada, sin duplicados por línea. */
  protected readonly voucherCandidates = computed(() => {
    const number = normalizeKey(this.voucherId());
    if (!number || !this.purchaseOrderId()) return [];
    const orderItemIds = new Set(this.selectedOrderItems().map((item) => item.id));
    const byApiId = new Map<string, DispatchVoucher>();
    for (const voucher of this.vouchers()) {
      if (byApiId.has(voucher.apiId)) continue;
      const sameNumber = normalizeKey(voucher.id) === number;
      const belongsToOrder = (voucher.lines ?? []).some((line) => orderItemIds.has(line.orderItemId));
      if (sameNumber && belongsToOrder) byApiId.set(voucher.apiId, voucher);
    }
    return [...byApiId.values()];
  });

  /** Si el número se repite entre emisores, el emisor escrito desempata. */
  protected readonly matchingVouchers = computed(() => {
    const candidates = this.voucherCandidates();
    if (candidates.length <= 1) return candidates;
    const issuer = normalizeKey(this.issuer());
    return candidates.filter((voucher) => normalizeKey(voucher.issuer) === issuer);
  });

  protected readonly issuerTypes = [{ value: 'INSTITUTION', label: 'Institución' }, { value: 'STATION', label: 'Estación' }];
  protected readonly branches = [{ value: 'San José', label: 'San José' }, { value: 'Santa Marta', label: 'Santa Marta' }];

  constructor() {
    effect(() => {
      const available = this.purchaseOrderOptions();
      if (!available.some((order) => order.value === this.purchaseOrderId())) {
        this.purchaseOrderId.set(available[0]?.value ?? '');
      }
    });

    effect(() => {
      const order = this.selectedOrder();
      if (order && !this.locked()) this.issuer.set(order.entity);
    });

    effect(() => {
      const candidates = this.voucherCandidates();
      const matches = this.matchingVouchers();
      const existing = matches.length === 1 ? matches[0] : undefined;
      if (existing) {
        this.issuer.set(existing.issuer);
        this.issuerType.set(existing.issuerType);
        const count = existing.lines?.length ?? 0;
        this.hint.set(
          `Vale existente: ${this.voucherAvailableLabel(existing)} disponibles en ${count} combustible${count === 1 ? '' : 's'}. Se conserva su historial.`,
        );
        this.locked.set(true);
      } else {
        this.locked.set(false);
        if (this.wasLocked) {
          this.issuer.set(this.selectedOrder()?.entity ?? '');
          this.issuerType.set('INSTITUTION');
        }
        this.hint.set(candidates.length > 1
          ? 'Hay vales con ese número de distintos emisores. Indica el emisor exacto.'
          : 'Vale nuevo: indica los galones autorizados por cada combustible.');
      }
      this.wasLocked = existing !== undefined;
    });

    effect(() => {
      const items = this.selectedOrderItems();
      const matches = this.matchingVouchers();
      const existing = matches.length === 1 ? matches[0] : null;
      const key = `${this.purchaseOrderId()}|${existing?.apiId ?? 'new'}`;
      if (key === this.linesKey) return;
      this.linesKey = key;
      this.lines.set(existing ? this.draftsFromVoucher(existing, items) : this.draftsFromOrder(items));
    });

    effect(() => {
      this.branchValue.set(this.branch() === 'Todas las sedes' ? 'San José' : this.branch());
    });

    effect(() => {
      const token = this.resetToken();
      if (token === this.previousToken) {
        return;
      }
      this.previousToken = token;
      this.voucherId.set('');
      this.institutionRuc.set('');
      this.purchaseOrderId.set('');
      this.issuer.set('');
      this.issuerType.set('INSTITUTION');
      this.error.set('');
      this.wasLocked = false;
      this.linesKey = '';
      this.lines.set([]);
    });
  }

  protected searchInstitutions(event: AutoCompleteCompleteEvent): void {
    const query = normalizeSearch(event.query);
    this.institutionSuggestions.set(
      this.institutionOptions().filter((option) => normalizeSearch(option.label).includes(query)),
    );
  }

  protected setVoucher(event: Event): void {
    this.voucherId.set((event.target as HTMLInputElement).value);
    this.error.set('');
  }

  protected setIssuer(event: Event): void {
    this.issuer.set((event.target as HTMLInputElement).value);
  }

  protected setLineAuthorized(orderItemId: string, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.lines.update((lines) => lines.map((line) =>
      line.orderItemId === orderItemId ? { ...line, authorized: value } : line,
    ));
    this.error.set('');
  }

  protected setLineGallons(orderItemId: string, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.lines.update((lines) => lines.map((line) =>
      line.orderItemId === orderItemId ? { ...line, gallons: value } : line,
    ));
    this.error.set('');
  }

  protected lineAvailableMilli(line: FuelDraft): number {
    return line.voucherAvailableMilli === null
      ? line.orderAvailableMilli
      : Math.min(line.orderAvailableMilli, line.voucherAvailableMilli);
  }

  protected lineAvailableLabel(line: FuelDraft): string {
    const milli = this.lineAvailableMilli(line);
    return milli > 0 ? `${formatGallons(milli / 1000)} gal` : 'sin saldo';
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const voucherId = this.voucherId().trim();

    if (!this.selectedOrderItems().length) {
      this.error.set('Selecciona una orden con saldo disponible.');
      return;
    }
    if (!voucherId) {
      this.error.set('Indica el número de vale.');
      return;
    }
    if (!this.locked() && !this.issuer().trim()) {
      this.error.set('Indica el nombre del emisor del vale.');
      return;
    }
    if (!this.lines().length) {
      this.error.set('La orden no tiene combustibles disponibles.');
      return;
    }

    const existing = this.locked() ? this.matchingVouchers()[0] : undefined;
    if (this.locked() && !existing) {
      this.error.set('El vale seleccionado ya no está disponible. Actualiza la lista.');
      return;
    }

    const requestLines: AttendanceLineRequest[] = [];
    for (const line of this.lines()) {
      const rawAuthorized = line.authorized.trim();
      const rawGallons = line.gallons.trim();
      if (existing) {
        if (!rawGallons) continue;
      } else if (!rawAuthorized && !rawGallons) {
        continue;
      }

      const authorized = rawAuthorized ? parseGallonsInput(rawAuthorized) : null;
      const gallons = rawGallons ? parseGallonsInput(rawGallons) : null;
      if (rawAuthorized && !authorized) {
        this.error.set(`${line.fuel}: los galones autorizados admiten hasta 3 decimales (ej. 50,250).`);
        return;
      }
      if (rawGallons && !gallons) {
        this.error.set(`${line.fuel}: los galones a entregar admiten hasta 3 decimales (ej. 5,250).`);
        return;
      }

      if (existing) {
        if (!gallons || gallons.milli <= 0) continue;
        if (gallons.milli > this.lineAvailableMilli(line)) {
          this.error.set(`${line.fuel}: el despacho supera el saldo disponible (${this.lineAvailableLabel(line)}).`);
          return;
        }
        requestLines.push({
          orderItemId: line.orderItemId,
          voucherItemId: line.voucherItemId,
          authorized: '0.000',
          gallons: gallons.normalized,
        });
        continue;
      }

      if (gallons && (!authorized || authorized.milli <= 0)) {
        this.error.set(`${line.fuel}: indica los galones autorizados del vale.`);
        return;
      }
      if (gallons && authorized && authorized.milli < gallons.milli) {
        this.error.set(`${line.fuel}: los galones autorizados deben cubrir el despacho.`);
        return;
      }
      if (gallons && gallons.milli > line.orderAvailableMilli) {
        this.error.set(`${line.fuel}: el despacho supera el saldo disponible de la orden.`);
        return;
      }
      requestLines.push({
        orderItemId: line.orderItemId,
        authorized: authorized?.normalized ?? '0.000',
        gallons: gallons?.normalized ?? '0.000',
      });
    }

    if (!requestLines.some((line) => gallonsToMilli(line.gallons) > 0)) {
      this.error.set('Indica los galones entregados de al menos un combustible.');
      return;
    }

    this.error.set('');
    this.register.emit({
      purchaseOrderId: this.purchaseOrderId(),
      voucherId,
      issuer: this.issuer().trim(),
      issuerType: this.issuerType(),
      branch: this.branchValue(),
      lines: requestLines,
    });
  }

  private voucherAvailableLabel(voucher: DispatchVoucher): string {
    const milli = (voucher.lines ?? []).reduce(
      (sum, line) => sum + gallonsBalanceMilli(line.authorized, line.attended),
      0,
    );
    return `${formatGallons(milli / 1000)} gal`;
  }

  private draftsFromOrder(items: readonly DispatchOrder[]): readonly FuelDraft[] {
    return items.map((item) => ({
      orderItemId: item.id,
      fuel: item.fuel,
      authorized: '',
      orderAvailableMilli: gallonsBalanceMilli(item.total, item.used),
      voucherAvailableMilli: null,
      gallons: '',
    }));
  }

  private draftsFromVoucher(
    voucher: DispatchVoucher,
    items: readonly DispatchOrder[],
  ): readonly FuelDraft[] {
    const byOrderItem = new Map(items.map((item) => [item.id, item]));
    return (voucher.lines ?? []).map((line) => {
      const order = byOrderItem.get(line.orderItemId);
      return {
        orderItemId: line.orderItemId,
        voucherItemId: line.id,
        fuel: line.fuel,
        authorized: draftAmount(line.authorized),
        orderAvailableMilli: order ? gallonsBalanceMilli(order.total, order.used) : 0,
        voucherAvailableMilli: gallonsBalanceMilli(line.authorized, line.attended),
        gallons: '',
      };
    });
  }
}

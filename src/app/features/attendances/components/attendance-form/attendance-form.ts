import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AutoCompleteModule, type AutoCompleteCompleteEvent } from 'primeng/autocomplete';
import { SelectModule } from 'primeng/select';
import { formatGallons, orderBalance } from '../../../orders/orders-data';
import { voucherBalance, type VoucherIssuerType } from '../../../vouchers/vouchers-data';
import type { AttendanceRequest } from '../../attendances-data';
import type { DispatchOrder, DispatchVoucher } from '../../operations-store';

interface InstitutionOption {
  readonly value: string;
  readonly label: string;
}

function normalizeSearch(value: string): string {
  return value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('es-PE').trim();
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

  protected readonly orderId = signal('');
  protected readonly institutionRuc = signal('');
  protected readonly institutionSuggestions = signal<InstitutionOption[]>([]);
  protected readonly purchaseOrderId = signal('');
  protected readonly voucherId = signal('');
  protected readonly issuer = signal('');
  protected readonly issuerType = signal<VoucherIssuerType>('INSTITUTION');
  protected readonly authorized = signal('');
  protected readonly gallons = signal('');
  protected readonly branchValue = signal('San José');
  protected readonly hint = signal('Para un vale nuevo, ingresa emisor y galones autorizados.');
  protected readonly locked = signal(false);
  protected readonly error = signal('');

  private previousToken = 0;
  private wasLocked = false;

  protected readonly selectedOrder = computed(
    () => this.filteredOrders().find((order) => order.id === this.orderId()) ?? null,
  );
  protected readonly institutionOptions = computed(() => {
    const byId = new Map<string, { value: string; label: string; orderIds: Set<string> }>();
    for (const order of this.orders()) {
      const current = byId.get(order.institutionRuc);
      byId.set(order.institutionRuc, {
        value: order.institutionRuc,
        label: current?.label ?? `${order.entity} · ${order.institutionRuc}`,
        orderIds: new Set([...(current?.orderIds ?? []), order.apiId]),
      });
    }
    return [...byId.values()]
      .sort((a, b) => a.label.localeCompare(b.label, 'es-PE'))
      .map((item) => ({
        value: item.value,
        label: `${item.label} · ${item.orderIds.size} ${item.orderIds.size === 1 ? 'orden disponible' : 'órdenes disponibles'}`,
      }));
  });
  protected readonly filteredOrders = computed(() =>
    this.orders().filter((order) => order.institutionRuc === this.institutionRuc()),
  );
  protected readonly orderBalanceLabel = computed(() => {
    const order = this.selectedOrder();
    return order ? `${formatGallons(orderBalance(order))} gal` : '— gal';
  });
  protected readonly purchaseOrderOptions = computed(() => {
    const byId = new Map<string, DispatchOrder>();
    for (const order of this.filteredOrders()) byId.set(order.apiId, order);
    return [...byId.values()].map((order) => ({
      value: order.apiId,
      label: `${order.orderNumber} · ${order.date} · ${order.branch}`,
    }));
  });
  protected readonly fuelLineOptions = computed(() => this.filteredOrders()
    .filter((order) => order.apiId === this.purchaseOrderId())
    .map((order) => ({
    value: order.id,
    label: `${order.fuel} · ${this.balance(order)} disponibles`,
  })));
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
      const available = this.filteredOrders().filter(
        (order) => order.apiId === this.purchaseOrderId(),
      );
      if (!available.some((order) => order.id === this.orderId())) {
        this.orderId.set(available[0]?.id ?? '');
      }
    });

    effect(() => {
      const order = this.selectedOrder();
      if (order && !this.locked()) this.issuer.set(order.entity);
    });

    effect(() => {
      const id = this.voucherId().trim().toLowerCase();
      const matches = id ? this.vouchers().filter((voucher) =>
        voucher.id.toLowerCase() === id && voucher.orderItemId === this.orderId(),
      ) : [];
      const existing = matches.length === 1 ? matches[0] : undefined;
      if (existing) {
        this.issuer.set(existing.issuer);
        this.issuerType.set(existing.issuerType);
        this.authorized.set(String(existing.total));
        this.hint.set(
          `Vale existente: ${formatGallons(voucherBalance(existing))} gal disponibles. Se conserva su historial.`,
        );
        this.locked.set(true);
      } else {
        this.locked.set(false);
        if (this.wasLocked) {
          this.issuer.set('');
          this.issuerType.set('INSTITUTION');
          this.authorized.set('');
        }
        this.hint.set(matches.length > 1
          ? 'Hay vales con ese número de distintos emisores. Indica el emisor exacto.'
          : 'Para un vale nuevo, ingresa emisor y galones autorizados.');
      }
      this.wasLocked = existing !== undefined;
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
      this.authorized.set('');
      this.gallons.set('');
      this.error.set('');
    });
  }

  protected balance(order: DispatchOrder): string {
    return `${formatGallons(orderBalance(order))} gal`;
  }

  protected searchInstitutions(event: AutoCompleteCompleteEvent): void {
    const query = normalizeSearch(event.query);
    this.institutionSuggestions.set(
      this.institutionOptions().filter((option) => normalizeSearch(option.label).includes(query)),
    );
  }

  protected setVoucher(event: Event): void {
    this.voucherId.set((event.target as HTMLInputElement).value);
  }

  protected setIssuer(event: Event): void {
    this.issuer.set((event.target as HTMLInputElement).value);
  }

  protected setAuthorized(event: Event): void {
    this.authorized.set((event.target as HTMLInputElement).value);
  }

  protected setGallons(event: Event): void {
    this.gallons.set((event.target as HTMLInputElement).value);
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    const order = this.selectedOrder();
    const voucherId = this.voucherId().trim();
    const gallons = Number(this.gallons());

    if (!order) {
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
    if (!Number.isFinite(gallons) || gallons <= 0) {
      this.error.set('Indica los galones realmente entregados.');
      return;
    }
    const normalize = (value: string) => value.normalize('NFKC').trim().toLocaleLowerCase().replace(/\s+/g, ' ');
    const existing = this.vouchers().find((voucher) =>
      voucher.orderItemId === order.id
      && normalize(voucher.id) === normalize(voucherId)
      && normalize(voucher.issuer) === normalize(this.issuer()),
    );
    if (gallons > orderBalance(order) || (existing && gallons > voucherBalance(existing))) {
      this.error.set('El despacho supera el saldo disponible de la orden o del vale.');
      return;
    }
    const authorized = Number(this.authorized());
    if (!existing && (!Number.isFinite(authorized) || authorized < gallons)) {
      this.error.set('Los galones autorizados deben cubrir el despacho.');
      return;
    }

    this.error.set('');
    this.register.emit({
      orderId: order.id,
      voucherId,
      issuer: this.issuer().trim(),
      issuerType: this.issuerType(),
      authorized,
      gallons,
      branch: this.branchValue(),
    });
  }
}

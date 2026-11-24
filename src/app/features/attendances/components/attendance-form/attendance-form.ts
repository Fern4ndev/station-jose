import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from '@angular/core';
import { formatGallons, orderBalance } from '../../../orders/orders-data';
import { voucherBalance, type VoucherIssuerType } from '../../../vouchers/vouchers-data';
import type { AttendanceRequest } from '../../attendances-data';
import type { DispatchOrder, DispatchVoucher } from '../../operations-store';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
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
    () => this.orders().find((order) => order.id === this.orderId()) ?? null,
  );
  protected readonly orderBalanceLabel = computed(() => {
    const order = this.selectedOrder();
    return order ? `${formatGallons(orderBalance(order))} gal` : '— gal';
  });

  constructor() {
    effect(() => {
      const available = this.orders();
      if (!available.some((order) => order.id === this.orderId())) {
        this.orderId.set(available[0]?.id ?? '');
      }
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

  protected setOrder(event: Event): void {
    this.orderId.set((event.target as HTMLSelectElement).value);
  }

  protected setVoucher(event: Event): void {
    this.voucherId.set((event.target as HTMLInputElement).value);
  }

  protected setIssuer(event: Event): void {
    this.issuer.set((event.target as HTMLInputElement).value);
  }

  protected setIssuerType(event: Event): void {
    this.issuerType.set((event.target as HTMLSelectElement).value as VoucherIssuerType);
  }

  protected setAuthorized(event: Event): void {
    this.authorized.set((event.target as HTMLInputElement).value);
  }

  protected setGallons(event: Event): void {
    this.gallons.set((event.target as HTMLInputElement).value);
  }

  protected setBranch(event: Event): void {
    this.branchValue.set((event.target as HTMLSelectElement).value);
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

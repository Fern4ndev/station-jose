import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from '@angular/core';
import { formatGallons, orderBalance, type DemoOrder } from '../../../orders/orders-data';
import {
  voucherBalance,
  type DemoVoucher,
  type VoucherIssuerType,
} from '../../../vouchers/vouchers-data';
import type { AttendanceRequest } from '../../attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-attendance-form',
  templateUrl: './attendance-form.html',
})
export class AttendanceForm {
  readonly orders = input.required<readonly DemoOrder[]>();
  readonly vouchers = input.required<readonly DemoVoucher[]>();
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
      const existing = id ? this.vouchers().find((voucher) => voucher.id.toLowerCase() === id) : undefined;
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
        this.hint.set('Para un vale nuevo, ingresa emisor y galones autorizados.');
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

  protected balance(order: DemoOrder): string {
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

    this.error.set('');
    this.register.emit({
      orderId: order.id,
      voucherId,
      issuer: this.issuer().trim(),
      issuerType: this.issuerType(),
      authorized: Number(this.authorized()),
      gallons,
      branch: this.branchValue(),
    });
  }
}

import {
  CUSTOM_ELEMENTS_SCHEMA,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  model,
  signal,
} from '@angular/core';
import { firstValueFrom } from 'rxjs';
import 'iconify-icon';
import type { VoucherDetail } from '../../../../core/models/voucher';
import { ISSUER_TYPE_LABELS, type VoucherIssuerType } from '../../../../core/models/voucher';
import { VouchersApi } from '../../../../core/services/vouchers-api';
import { TableRefresh } from '../../../../shared/components/table-refresh/table-refresh';
import type { StatusTone } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { extractApiError } from '../../../../shared/utils/api-error';
import { formatGallons, orderBalance, type DemoOrder } from '../../orders-data';
import { voucherStatus, type VoucherStatus } from '../../../vouchers/vouchers-data';
import { VoucherDetailDialog } from '../voucher-detail-dialog/voucher-detail-dialog';

type OrderDetailTab = 'summary' | 'vouchers';

export interface VoucherLineView {
  readonly id: string;
  readonly fuel: string;
  readonly authorized: number;
  readonly attended: number;
  readonly available: number;
}

export interface AttendanceFuelView {
  readonly id: string;
  readonly fuel: string;
  readonly gallons: number;
}

export interface VoucherAttendanceView {
  readonly id: string;
  readonly date: string;
  readonly time: string;
  readonly performer: string;
  readonly branch: string;
  readonly gallons: number;
  readonly fuels: readonly AttendanceFuelView[];
}

export interface VoucherView {
  readonly id: string;
  readonly number: string;
  readonly issuer: string;
  readonly issuerType: string;
  readonly createdLabel: string;
  readonly createdAt: string;
  readonly lastAttendedAt: string | null;
  readonly status: VoucherStatus;
  readonly total: number;
  readonly used: number;
  readonly balance: number;
  readonly lines: readonly VoucherLineView[];
  readonly attendances: readonly VoucherAttendanceView[];
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TableRefresh, UiDialog, UiStatusBadge, VoucherDetailDialog],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  selector: 'app-order-detail-dialog',
  templateUrl: './order-detail-dialog.html',
})
export class OrderDetailDialog {
  readonly visible = model(false);
  readonly order = input<DemoOrder | null>(null);

  private readonly vouchersApi = inject(VouchersApi);
  private shownOrderId: string | null = null;
  private loadedOrderId: string | null = null;

  protected readonly tab = signal<OrderDetailTab>('summary');
  protected readonly vouchers = signal<readonly VoucherView[]>([]);
  protected readonly loading = signal(false);
  protected readonly loaded = signal(false);
  protected readonly error = signal('');
  protected readonly selectedVoucher = signal<VoucherView | null>(null);
  protected readonly voucherOpen = signal(false);

  protected readonly authorizedTotal = computed(() =>
    (this.order()?.source?.items ?? []).reduce((sum, item) => sum + Number(item.authorized_gallons), 0),
  );

  protected readonly attendedTotal = computed(() =>
    (this.order()?.source?.items ?? []).reduce((sum, item) => sum + Number(item.attended_gallons), 0),
  );

  protected readonly availableTotal = computed(() => {
    const items = this.order()?.source?.items ?? [];
    if (items.length > 0) {
      return items.reduce((sum, item) => sum + Number(item.available_gallons), 0);
    }
    const order = this.order();
    return order ? orderBalance(order) : 0;
  });

  protected readonly balance = computed(() => `${formatGallons(this.availableTotal())} gal`);

  protected readonly usedPercent = computed(() => this.percent(this.attendedTotal(), this.authorizedTotal()));

  protected readonly voucherAttended = computed(() =>
    this.vouchers().reduce((sum, voucher) => sum + voucher.used, 0),
  );

  protected readonly voucherBalance = computed(() =>
    this.vouchers().reduce((sum, voucher) => sum + voucher.balance, 0),
  );

  constructor() {
    effect(() => {
      const visible = this.visible();
      const orderId = this.order()?.apiId ?? null;
      if (!visible) {
        this.shownOrderId = null;
        this.loadedOrderId = null;
        this.voucherOpen.set(false);
        this.selectedVoucher.set(null);
        return;
      }
      if (orderId === this.shownOrderId) return;
      // Cada orden se abre en Resumen y con los vales sin cargar.
      this.shownOrderId = orderId;
      this.loadedOrderId = null;
      this.tab.set('summary');
      this.vouchers.set([]);
      this.loaded.set(false);
      this.error.set('');
      this.selectedVoucher.set(null);
      this.voucherOpen.set(false);
    });
  }

  protected selectTab(tab: OrderDetailTab): void {
    this.tab.set(tab);
    if (tab === 'vouchers' && this.loadedOrderId !== (this.order()?.apiId ?? null)) {
      void this.loadVouchers();
    }
  }

  protected reloadVouchers(): void {
    void this.loadVouchers();
  }

  protected openVoucher(voucher: VoucherView): void {
    this.selectedVoucher.set(voucher);
    this.voucherOpen.set(true);
  }

  protected gallons(value: number | string): string {
    return `${formatGallons(Number(value))} gal`;
  }

  protected attendedLabel(voucher: VoucherView): string {
    return `${formatGallons(voucher.used)} / ${formatGallons(voucher.total)} gal`;
  }

  /** Normaliza galones que llegan como número o cadena desde la API. */
  protected num(value: number | string): number {
    return Number(value);
  }

  protected percent(value: number, total: number): number {
    if (total <= 0) return 0;
    return Math.min(100, Math.max(0, Math.round((value / total) * 100)));
  }

  protected hasBalance(voucher: VoucherView): boolean {
    return voucher.balance > 0;
  }

  protected statusTone(status: VoucherStatus): StatusTone {
    if (status === 'Disponible') return 'green';
    if (status === 'Bloqueado') return 'gray';
    return 'amber';
  }

  private async loadVouchers(): Promise<void> {
    const order = this.order();
    const orderId = order?.apiId;
    if (!order || !orderId || this.loading()) return;

    this.loading.set(true);
    this.error.set('');
    try {
      const vouchers: VoucherDetail[] = [];
      for (let page = 1; ; page += 1) {
        const result = await firstValueFrom(
          this.vouchersApi.list({ purchase_order_id: orderId, page, page_size: 100 }),
        );
        for (const item of result.items) vouchers.push(item);
        if (page >= result.pagination.pages) break;
      }
      if (this.order()?.apiId !== orderId) return;
      this.vouchers.set(this.toVoucherViews(vouchers, order));
      this.loaded.set(true);
      this.loadedOrderId = orderId;
    } catch (error) {
      if (this.order()?.apiId === orderId) {
        this.error.set(extractApiError(error, 'No se pudieron cargar los vales de la orden.'));
      }
    } finally {
      this.loading.set(false);
    }
  }

  private toVoucherViews(items: readonly VoucherDetail[], order: DemoOrder): VoucherView[] {
    const fuelByOrderItem = new Map<string, string>(
      (order.source?.items ?? []).map((item) => [item.id, item.fuel_type.name] as const),
    );

    return items
      .map((voucher): VoucherView => {
        const lines: VoucherLineView[] = voucher.items.map((line) => ({
          id: line.id,
          fuel: fuelByOrderItem.get(line.purchase_order_item_id) ?? 'Combustible',
          authorized: Number(line.authorized_gallons),
          attended: Number(line.attended_gallons),
          available: Number(line.available_gallons),
        }));
        const lineById = new Map(voucher.items.map((line) => [line.id, line] as const));
        const total = lines.reduce((sum, line) => sum + line.authorized, 0);
        const used = lines.reduce((sum, line) => sum + line.attended, 0);

        const attendances: VoucherAttendanceView[] = [...voucher.attendances]
          .sort((a, b) => b.attended_at.localeCompare(a.attended_at))
          .map((attendance) => {
            const fuels: AttendanceFuelView[] = attendance.items.map((item) => {
              const line = lineById.get(item.voucher_item_id);
              return {
                id: item.id,
                fuel: fuelByOrderItem.get(line?.purchase_order_item_id ?? '') ?? 'Combustible',
                gallons: Number(item.attended_gallons),
              };
            });
            const at = new Date(attendance.attended_at);
            return {
              id: attendance.id,
              date: at
                .toLocaleDateString('es-PE', {
                  day: '2-digit',
                  month: 'short',
                  year: 'numeric',
                  timeZone: 'America/Lima',
                })
                .replace(/\./g, ''),
              time: at.toLocaleTimeString('es-PE', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'America/Lima',
              }),
              performer: attendance.performer_name ?? '—',
              branch: attendance.branch_name ?? order.branch,
              gallons: fuels.reduce((sum, fuel) => sum + fuel.gallons, 0),
              fuels,
            };
          });

        const createdAt = new Date(voucher.created_at);
        const lastAttendedAt = attendances.length > 0
          ? [...voucher.attendances].sort((a, b) => b.attended_at.localeCompare(a.attended_at))[0].attended_at
          : null;

        return {
          id: voucher.id,
          number: voucher.voucher_number,
          issuer: voucher.issuer_name,
          issuerType: ISSUER_TYPE_LABELS[voucher.issuer_type as VoucherIssuerType] ?? voucher.issuer_type,
          createdLabel: `${createdAt
            .toLocaleDateString('es-PE', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
              timeZone: 'America/Lima',
            })
            .replace(/\./g, '')} · ${createdAt.toLocaleTimeString('es-PE', {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'America/Lima',
          })}`,
          createdAt: voucher.created_at,
          lastAttendedAt,
          status: voucherStatus({
            id: voucher.voucher_number,
            orderId: order.id,
            issuer: voucher.issuer_name,
            issuerType: voucher.issuer_type as VoucherIssuerType,
            fuel: lines.map((line) => line.fuel).join(', '),
            total,
            used,
            backendStatus: voucher.status,
          }),
          total,
          used,
          balance: Math.max(0, total - used),
          lines,
          attendances,
        };
      })
      // El vale con la atención más reciente ocupa la fila 1.
      .sort((a, b) => (b.lastAttendedAt ?? b.createdAt).localeCompare(a.lastAttendedAt ?? a.createdAt));
  }
}

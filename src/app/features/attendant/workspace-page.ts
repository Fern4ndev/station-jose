import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { Subject, catchError, map, of, switchMap } from 'rxjs';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';
import { OrderSearch } from './order-search/order-search';
import { VoucherSearch } from './voucher-search/voucher-search';
import { PurchaseOrder, PurchaseOrderApi } from '../purchase-orders/purchase-order-api';
import { VoucherApi, VoucherDetail } from '../vouchers/voucher-api';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState, OrderSearch, PageHeader, SectionPanel, VoucherSearch],
  selector: 'app-attendant-workspace-page',
  styleUrl: './workspace-page.css',
  templateUrl: './workspace-page.html',
})
export class WorkspacePage {
  private readonly route = inject(ActivatedRoute);
  private readonly ordersApi = inject(PurchaseOrderApi);
  private readonly vouchersApi = inject(VoucherApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly orderQueries = new Subject<string>();
  private readonly voucherQueries = new Subject<string>();
  protected readonly title = String(this.route.snapshot.data['title'] ?? 'Espacio de atención');
  protected readonly description = String(this.route.snapshot.data['description'] ?? 'Consulta órdenes, vales y sus saldos.');
  protected readonly orders = signal<readonly PurchaseOrder[]>([]);
  protected readonly vouchers = signal<readonly VoucherDetail[]>([]);
  protected readonly orderState = signal<'initial' | 'loading' | 'ready' | 'error'>('initial');
  protected readonly voucherState = signal<'initial' | 'loading' | 'ready' | 'error'>('initial');

  constructor() {
    this.orderQueries.pipe(switchMap((query) => {
      if (query.length < 2) return of({ state: 'initial' as const, items: [] });
      this.orderState.set('loading');
      return this.ordersApi.search(query).pipe(map((result) => ({ state: 'ready' as const, items: result.items })), catchError(() => of({ state: 'error' as const, items: [] })));
    }), takeUntilDestroyed(this.destroyRef)).subscribe((result) => { this.orders.set(result.items); this.orderState.set(result.state); });
    this.voucherQueries.pipe(switchMap((query) => {
      if (query.length < 2) return of({ state: 'initial' as const, items: [] });
      this.voucherState.set('loading');
      return this.vouchersApi.search(query).pipe(map((result) => ({ state: 'ready' as const, items: result.items })), catchError(() => of({ state: 'error' as const, items: [] })));
    }), takeUntilDestroyed(this.destroyRef)).subscribe((result) => { this.vouchers.set(result.items); this.voucherState.set(result.state); });
  }

  protected searchOrders(query: string): void { this.orderQueries.next(query); }
  protected searchVouchers(query: string): void { this.voucherQueries.next(query); }
}

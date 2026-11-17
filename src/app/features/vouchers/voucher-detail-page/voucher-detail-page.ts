import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthStore } from '../../../core/services/auth/auth';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { PurchaseOrderApi } from '../../purchase-orders/purchase-order-api';
import { VoucherApi, VoucherDetail } from '../voucher-api';
import { forkJoin, of, switchMap } from 'rxjs';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SectionPanel], selector: 'app-voucher-detail-page', templateUrl: './voucher-detail-page.html' })
export class VoucherDetailPage {
  protected readonly voucherId = inject(ActivatedRoute).snapshot.paramMap.get('voucherId') ?? '';
  private readonly api = inject(VoucherApi);
  private readonly orders = inject(PurchaseOrderApi);
  private readonly auth = inject(AuthStore);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly state = signal<'loading' | 'error' | 'ready' | 'unavailable'>('loading');
  protected readonly voucher = signal<VoucherDetail | null>(null);
  protected readonly names = signal<ReadonlyMap<string, string>>(new Map());
  constructor() { this.load(); }
  protected load(): void {
    if (this.auth.user()?.role === 'ATTENDANT') { this.state.set('unavailable'); return; }
    this.state.set('loading');
    this.api.get(this.voucherId).pipe(
      switchMap((voucher) => forkJoin({ voucher: of(voucher), order: this.orders.get(voucher.purchase_order_id) })),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({ voucher, order }) => {
        this.voucher.set(voucher);
        this.names.set(new Map(order.items.map((item) => [item.id, item.fuel_type.name])));
        this.state.set('ready');
      },
      error: () => this.state.set('error'),
    });
  }
}

import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Subject, catchError, map, of, switchMap } from 'rxjs';
import { AuthStore } from '../../../core/services/auth/auth';
import { PurchaseOrder, PurchaseOrderApi } from '../../purchase-orders/purchase-order-api';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { BalanceLookup } from '../balance-lookup/balance-lookup';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [BalanceLookup, EmptyState, PageHeader, RouterLink, SectionPanel], selector: 'app-balances-page', templateUrl: './balances-page.html' })
export class BalancesPage {
  private readonly api = inject(PurchaseOrderApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly search = new Subject<string>();
  protected readonly available = inject(AuthStore).hasPermission('balances.read');
  protected readonly orders = signal<readonly PurchaseOrder[]>([]);
  protected readonly state = signal<'initial' | 'loading' | 'ready' | 'error'>('initial');

  constructor() {
    this.search.pipe(switchMap((query) => {
      if (query.length < 2) return of({ state: 'initial' as const, items: [] });
      this.state.set('loading');
      return this.api.search(query).pipe(
        map((response) => ({ state: 'ready' as const, items: response.items })),
        catchError(() => of({ state: 'error' as const, items: [] })),
      );
    }), takeUntilDestroyed(this.destroyRef)).subscribe((result) => {
      this.orders.set(result.items);
      this.state.set(result.state);
    });
  }

  protected onSearch(query: string): void { if (this.available) this.search.next(query); }
}

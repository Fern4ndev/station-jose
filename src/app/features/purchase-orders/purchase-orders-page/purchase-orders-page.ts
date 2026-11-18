import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Subject, catchError, map, of, switchMap } from 'rxjs';
import { TableModule } from 'primeng/table';
import { AuthStore } from '../../../core/services/auth/auth';
import { CatalogApi, CatalogItem } from '../../../core/services/catalog-api';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SearchField } from '../../../shared/components/search-field/search-field';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ServerPagination } from '../../../shared/components/server-pagination/server-pagination';
import { OrderFilters, PurchaseOrder, PurchaseOrderApi } from '../purchase-order-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, EmptyState, LoadingSkeleton, PageHeader, ReactiveFormsModule, RouterLink, SearchField, SectionPanel, ServerPagination, TableModule], selector: 'app-purchase-orders-page', templateUrl: './purchase-orders-page.html' })
export class PurchaseOrdersPage {
  protected readonly auth = inject(AuthStore);
  private readonly api = inject(PurchaseOrderApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly catalog = inject(CatalogApi);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly requests = new Subject<{ query: string; page: number }>();
  protected readonly query = signal('');
  protected readonly rows = signal<PurchaseOrder[]>([]);
  protected readonly page = signal(1);
  protected readonly pages = signal(0);
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly catalogError = signal(false);
  protected readonly filterError = signal('');
  protected readonly filters = this.fb.group({ branchId: '', dateFrom: '', dateTo: '', sortBy: 'issue_date' as OrderFilters['sortBy'], sortOrder: 'desc' as OrderFilters['sortOrder'] });
  protected readonly state = signal<'loading' | 'ready' | 'error' | 'unavailable'>('loading');
  constructor() {
    this.requests.pipe(switchMap(({ query, page }) => {
      this.state.set('loading');
      return this.api.search(query, page, this.filters.getRawValue()).pipe(map((result) => ({ result })), catchError(() => of({ result: null })));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(({ result }) => {
      if (!result) { this.state.set('error'); return; }
      this.rows.set([...result.items]); this.page.set(result.pagination.page); this.pages.set(result.pagination.pages); this.state.set('ready');
    });
    this.load(1);
    this.loadBranches();
  }
  protected loadBranches(): void {
    this.catalogError.set(false);
    this.catalog.branches().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: (items) => this.branches.set(items.filter((item) => item.is_active)), error: () => this.catalogError.set(true) });
  }
  protected load(page: number): void {
    const { dateFrom, dateTo } = this.filters.getRawValue();
    if (dateFrom && dateTo && dateFrom > dateTo) { this.filterError.set('La fecha inicial no puede ser posterior a la final.'); return; }
    this.filterError.set(''); this.requests.next({ query: this.query(), page });
  }
  protected search(query: string): void { this.query.set(query); this.load(1); }
}

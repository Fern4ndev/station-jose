import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, map, of, Subject, switchMap } from 'rxjs';
import { TableModule } from 'primeng/table';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SearchField } from '../../../shared/components/search-field/search-field';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ServerPagination } from '../../../shared/components/server-pagination/server-pagination';
import { VoucherApi, VoucherDetail } from '../voucher-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SearchField, SectionPanel, ServerPagination, TableModule], selector: 'app-vouchers-page', templateUrl: './vouchers-page.html' })
export class VouchersPage {
  private readonly api = inject(VoucherApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly requests = new Subject<{ query: string; page: number }>();
  protected readonly query = signal('');
  protected readonly rows = signal<VoucherDetail[]>([]);
  protected readonly state = signal<'loading' | 'error' | 'ready'>('loading');
  protected readonly page = signal(1);
  protected readonly pages = signal(0);
  constructor() {
    this.requests.pipe(switchMap(({ query, page }) => {
      this.state.set('loading');
      return this.api.search(query, page).pipe(map((result) => ({ result })), catchError(() => of({ result: null })));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(({ result }) => {
      if (!result) { this.state.set('error'); return; }
      this.rows.set([...result.items]); this.page.set(result.pagination.page); this.pages.set(result.pagination.pages); this.state.set('ready');
    });
    this.load(1);
  }
  protected load(page: number): void { this.requests.next({ query: this.query(), page }); }
  protected search(query: string): void { this.query.set(query); this.load(1); }
}

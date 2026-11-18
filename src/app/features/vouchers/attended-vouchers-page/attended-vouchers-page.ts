import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, map, of, Subject, switchMap } from 'rxjs';
import { TableModule } from 'primeng/table';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SearchField } from '../../../shared/components/search-field/search-field';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ServerPagination } from '../../../shared/components/server-pagination/server-pagination';
import { VoucherApi } from '../voucher-api';
import type { VoucherDetail } from '../voucher-api';

interface AttendedVoucherRow extends VoucherDetail {
  readonly lastAttendedAt: string;
}

interface VoucherPageRequest {
  readonly number: string;
  readonly page: number;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SearchField, SectionPanel, ServerPagination, TableModule],
  selector: 'app-attended-vouchers-page',
  templateUrl: './attended-vouchers-page.html',
})
export class AttendedVouchersPage {
  private readonly api = inject(VoucherApi);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly requests = new Subject<VoucherPageRequest>();

  protected readonly query = signal('');
  protected readonly rows = signal<readonly AttendedVoucherRow[]>([]);
  protected readonly state = signal<'loading' | 'error' | 'ready'>('loading');
  protected readonly page = signal(1);
  protected readonly pages = signal(0);
  protected readonly notice = this.route.snapshot.queryParamMap.has('registered');

  constructor() {
    this.requests
      .pipe(
        switchMap(({ number, page }) => {
          this.state.set('loading');
          return this.api.attended(number, page).pipe(
            map((result) => ({ result, error: false })),
            catchError(() => of({ result: null, error: true })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ result, error }) => {
        if (error || !result) {
          this.state.set('error');
          return;
        }

        const rows = result.items.map((voucher) => ({
          ...voucher,
          lastAttendedAt: voucher.attendances.reduce(
            (latest, attendance) => attendance.attended_at > latest ? attendance.attended_at : latest,
            voucher.attendances[0]?.attended_at ?? voucher.created_at,
          ),
        }));
        this.rows.set(rows);
        this.page.set(result.pagination.page);
        this.pages.set(result.pagination.pages);
        this.state.set('ready');
      });

    this.load('', 1);
  }

  protected load(number: string, page: number): void {
    this.query.set(number);
    this.requests.next({ number, page });
  }

  protected search(number: string): void {
    this.load(number.trim(), 1);
  }

  protected changePage(page: number): void {
    this.load(this.query(), page);
  }
}

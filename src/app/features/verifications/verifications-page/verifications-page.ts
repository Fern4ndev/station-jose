import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TableModule } from 'primeng/table';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { PendingVerification, VerificationApi } from '../verification-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SectionPanel, TableModule], selector: 'app-verifications-page', templateUrl: './verifications-page.html' })
export class VerificationsPage {
  private readonly api = inject(VerificationApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly reviewed = inject(ActivatedRoute).snapshot.queryParamMap.get('reviewed') === '1';
  protected readonly rows = signal<PendingVerification[]>([]);
  protected readonly state = signal<'loading' | 'error' | 'success'>('loading');

  constructor() { this.load(); }

  protected load(): void {
    this.state.set('loading');
    this.api.pending().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (rows) => { this.rows.set(rows); this.state.set('success'); },
      error: () => this.state.set('error'),
    });
  }
}

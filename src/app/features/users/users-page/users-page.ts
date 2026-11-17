import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { TableModule } from 'primeng/table';
import { AuthenticatedUser, ROLE_LABELS } from '../../../core/models/auth.models';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ServerPagination } from '../../../shared/components/server-pagination/server-pagination';
import { StatusBadge } from '../../../shared/components/status-badge/status-badge';
import { UsersApi } from '../users-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SectionPanel, ServerPagination, StatusBadge, TableModule], selector: 'app-users-page', templateUrl: './users-page.html' })
export class UsersPage {
  private readonly api = inject(UsersApi);
  private readonly destroyRef = inject(DestroyRef);
  protected roleLabel(role: unknown): string {
    return role === 'ADMIN' || role === 'OFFICE' || role === 'ATTENDANT' ? ROLE_LABELS[role] : 'Desconocido';
  }
  protected readonly rows = signal<AuthenticatedUser[]>([]);
  protected readonly state = signal<'loading' | 'error' | 'ready'>('loading');
  protected readonly page = signal(1);
  protected readonly pages = signal(0);
  constructor() { this.load(1); }
  protected load(page: number): void {
    this.state.set('loading');
    this.api.list(page).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => { this.rows.set([...result.items]); this.page.set(result.pagination.page); this.pages.set(result.pagination.pages); this.state.set('ready'); },
      error: () => this.state.set('error'),
    });
  }
}

import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { AuthStore } from '../../core/services/auth/auth';
import { CatalogApi, CatalogItem } from '../../core/services/catalog-api';
import { ApiError } from '../../shared/components/api-error/api-error';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';
import { DashboardChart } from './dashboard-chart/dashboard-chart';
import { DashboardShortcut } from './dashboard-shortcut/dashboard-shortcut';
import { DashboardApi, DashboardQuery, DashboardResponse } from './dashboard-api';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ApiError, DashboardChart, DashboardShortcut, DatePipe, EmptyState, LoadingSkeleton, PageHeader, ReactiveFormsModule, SectionPanel],
  selector: 'app-dashboard-page',
  styleUrl: './dashboard-page.css',
  templateUrl: './dashboard-page.html',
})
export class DashboardPage {
  protected readonly auth = inject(AuthStore);
  private readonly api = inject(DashboardApi);
  private readonly catalog = inject(CatalogApi);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly destroyRef = inject(DestroyRef);
  protected readonly filters = this.fb.group({ dateFrom: '', dateTo: '', branchId: '', groupBy: 'day' as DashboardQuery['groupBy'] });
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly filterError = signal('');
  protected readonly catalogError = signal(false);
  protected readonly data = signal<DashboardResponse | null>(null);
  protected readonly state = signal<'loading' | 'error' | 'success'>('loading');
  protected readonly periodLabels = computed(() => this.data()?.by_period.map((item) => item.period) ?? []);
  protected readonly gallonsByPeriod = computed(() => this.data()?.by_period.map((item) => Number(item.attended_gallons)) ?? []);

  constructor() {
    this.loadBranches();
    this.load();
  }

  protected loadBranches(): void {
    this.catalogError.set(false);
    this.catalog.branches().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: (items) => this.branches.set(items.filter((item) => item.is_active)), error: () => this.catalogError.set(true) });
  }

  protected load(): void {
    const query = this.filters.getRawValue();
    if (query.dateFrom && query.dateTo && query.dateFrom > query.dateTo) { this.filterError.set('La fecha inicial no puede ser posterior a la final.'); return; }
    this.filterError.set('');
    this.state.set('loading');
    this.api.getDashboard(query).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => { this.data.set(data); this.state.set('success'); },
      error: () => this.state.set('error'),
    });
  }
}

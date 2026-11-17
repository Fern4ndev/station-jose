import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { AuthStore } from '../../core/services/auth/auth';
import { ApiError } from '../../shared/components/api-error/api-error';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';
import { DashboardChart } from './dashboard-chart/dashboard-chart';
import { DashboardShortcut } from './dashboard-shortcut/dashboard-shortcut';
import { DashboardApi, DashboardResponse } from './dashboard-api';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ApiError, DashboardChart, DashboardShortcut, DatePipe, EmptyState, LoadingSkeleton, PageHeader, SectionPanel],
  selector: 'app-dashboard-page',
  styleUrl: './dashboard-page.css',
  templateUrl: './dashboard-page.html',
})
export class DashboardPage {
  protected readonly auth = inject(AuthStore);
  private readonly api = inject(DashboardApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly data = signal<DashboardResponse | null>(null);
  protected readonly state = signal<'loading' | 'error' | 'success'>('loading');
  protected readonly periodLabels = computed(() => this.data()?.by_period.map((item) => item.period) ?? []);
  protected readonly gallonsByPeriod = computed(() => this.data()?.by_period.map((item) => Number(item.attended_gallons)) ?? []);

  constructor() {
    this.load();
  }

  protected load(): void {
    this.state.set('loading');
    this.api.getDashboard().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => { this.data.set(data); this.state.set('success'); },
      error: () => this.state.set('error'),
    });
  }
}

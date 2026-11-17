import { ChangeDetectionStrategy, Component } from '@angular/core';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';
import { DashboardChart } from './dashboard-chart/dashboard-chart';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DashboardChart, EmptyState, PageHeader, SectionPanel],
  selector: 'app-dashboard-page',
  styleUrl: './dashboard-page.css',
  templateUrl: './dashboard-page.html',
})
export class DashboardPage {
  protected readonly periodLabels: readonly string[] = [];
  protected readonly gallonsByPeriod: readonly number[] = [];
}

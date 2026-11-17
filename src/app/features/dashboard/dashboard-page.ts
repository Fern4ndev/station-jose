import { ChangeDetectionStrategy, Component } from '@angular/core';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState, PageHeader, SectionPanel],
  selector: 'app-dashboard-page',
  styleUrl: './dashboard-page.css',
  templateUrl: './dashboard-page.html',
})
export class DashboardPage {}

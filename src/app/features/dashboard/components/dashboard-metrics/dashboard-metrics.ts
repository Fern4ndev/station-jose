import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import {
  UiStatCard,
  type StatCardModel,
} from '../../../../shared/components/ui-stat-card/ui-stat-card';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiStatCard],
  selector: 'app-dashboard-metrics',
  templateUrl: './dashboard-metrics.html',
})
export class DashboardMetrics {
  readonly metrics = input.required<readonly StatCardModel[]>();
}

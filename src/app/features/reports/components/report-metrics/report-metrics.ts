import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import {
  UiStatCard,
  type StatCardModel,
} from '../../../../shared/components/ui-stat-card/ui-stat-card';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiStatCard],
  selector: 'app-report-metrics',
  templateUrl: './report-metrics.html',
})
export class ReportMetrics {
  readonly metrics = input.required<readonly StatCardModel[]>();
}

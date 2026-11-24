import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import type { ReportBucket } from '../../reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiPanel, UiStatusBadge],
  selector: 'app-report-chart',
  templateUrl: './report-chart.html',
})
export class ReportChart {
  readonly buckets = input.required<readonly ReportBucket[]>();
  readonly badge = input('');

  private readonly max = computed(() =>
    Math.max(1, ...this.buckets().flatMap((bucket) => [bucket.sanJose, bucket.santaMarta])),
  );

  protected height(value: number): number {
    return Math.max(4, Math.round((value / this.max()) * 100));
  }
}

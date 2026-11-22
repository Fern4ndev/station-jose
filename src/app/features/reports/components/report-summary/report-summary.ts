import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import type { ReportSummary } from '../../reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiPanel],
  selector: 'app-report-summary',
  templateUrl: './report-summary.html',
})
export class ReportSummaryPanel {
  readonly summary = input.required<ReportSummary>();

  protected readonly width = computed(() => `${Math.min(100, Math.max(0, this.summary().percent))}%`);
}

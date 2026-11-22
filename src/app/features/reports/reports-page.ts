import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { UiToast } from '../../shared/components/ui-toast/ui-toast';
import { ReportChart } from './components/report-chart/report-chart';
import { ReportMetrics } from './components/report-metrics/report-metrics';
import { ReportSummaryPanel } from './components/report-summary/report-summary';
import {
  REPORT_DATASETS,
  REPORT_PERIODS,
  buildReportCsv,
  buildReportMetrics,
  buildReportSummary,
  reportFileName,
  type ReportPeriod,
} from './reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReportChart, ReportMetrics, ReportSummaryPanel, UiIcon, UiPageHeading, UiToast],
  selector: 'app-reports-page',
  templateUrl: './reports-page.html',
})
export class ReportsPage {
  private readonly state = inject(AdminUiState);
  private readonly messages = inject(MessageService);

  protected readonly periods = REPORT_PERIODS;
  protected readonly period = signal<ReportPeriod>('7d');
  protected readonly branch = this.state.branch;

  protected readonly dataset = computed(() => REPORT_DATASETS[this.period()]);
  protected readonly metrics = computed(() =>
    buildReportMetrics(this.dataset(), this.branch()),
  );
  protected readonly summary = computed(() => buildReportSummary(this.branch()));

  protected onPeriod(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as ReportPeriod;
    this.period.set(value);
    const label = this.periods.find((option) => option.value === value)?.label ?? value;
    this.messages.add({ severity: 'info', summary: `Período seleccionado: ${label}.`, life: 2600 });
  }

  protected exportCsv(): void {
    const csv = buildReportCsv(this.branch());
    const blob = new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = reportFileName(this.branch());
    link.click();
    URL.revokeObjectURL(url);
    this.messages.add({
      severity: 'success',
      summary: 'Reporte de saldos descargado como CSV de demostración.',
      life: 2800,
    });
  }
}

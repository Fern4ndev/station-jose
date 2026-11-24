import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { ChartModule } from 'primeng/chart';
import type { ChartData, ChartOptions } from 'chart.js';
import type { ReportBucket } from '../../reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiPanel, UiStatusBadge, ChartModule],
  selector: 'app-report-chart',
  templateUrl: './report-chart.html',
})
export class ReportChart {
  readonly buckets = input.required<readonly ReportBucket[]>();
  readonly badge = input('');

  protected readonly chartData = computed<ChartData<'bar'>>(() => ({
    labels: this.buckets().map((bucket) => bucket.label),
    datasets: [
      {
        label: 'San José',
        data: this.buckets().map((bucket) => bucket.sanJose),
        backgroundColor: '#50b49f',
        hoverBackgroundColor: '#43a28e',
        borderRadius: 4,
        maxBarThickness: 26,
      },
      {
        label: 'Santa Marta',
        data: this.buckets().map((bucket) => bucket.santaMarta),
        backgroundColor: '#9dcfc4',
        hoverBackgroundColor: '#8bc3b6',
        borderRadius: 4,
        maxBarThickness: 26,
      },
    ],
  }));

  protected readonly chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 240 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#52636a', boxWidth: 10, boxHeight: 10, usePointStyle: true, font: { size: 10 } },
      },
      tooltip: {
        backgroundColor: '#22373e',
        titleFont: { size: 11, weight: 600 },
        bodyFont: { size: 11 },
        padding: 10,
        cornerRadius: 8,
        callbacks: {
          label: (context) => ` ${context.dataset.label}: ${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(Number(context.parsed.y ?? 0))} gal`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: '#65777b', maxRotation: 45, minRotation: 0, font: { size: 10 } },
        grid: { display: false },
        border: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: '#65777b',
          font: { size: 10 },
          callback: (value) => new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(Number(value)),
        },
        grid: { color: 'rgba(229, 234, 234, 0.9)' },
        border: { display: false },
        title: { display: true, text: 'Galones', color: '#8c999d', font: { size: 10, weight: 500 } },
      },
    },
  };
}

import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectModule } from 'primeng/select';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import { ChartModule } from 'primeng/chart';
import type { ChartData, ChartOptions } from 'chart.js';
import type { ReportBucket } from '../../reports-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiPanel, FormsModule, SelectModule, ChartModule],
  selector: 'app-report-chart',
  templateUrl: './report-chart.html',
})
export class ReportChart {
  readonly buckets = input.required<readonly ReportBucket[]>();
  readonly badge = input('');
  readonly subtitle = input('Actividad por sede');
  readonly loading = input(false);
  readonly hourly = input(false);
  protected readonly selectedBranch = signal<'all' | 'sanJose' | 'santaMarta'>('all');
  protected readonly branchOptions = [
    { value: 'all', label: 'Ambas sedes' },
    { value: 'sanJose', label: 'San José' },
    { value: 'santaMarta', label: 'Santa Marta' },
  ];
  protected readonly minimumWidth = computed(() => Math.max(260, this.buckets().length * (this.hourly() ? 16 : 24)));
  protected readonly hasActivity = computed(() => this.buckets().some((bucket) =>
    (this.selectedBranch() !== 'santaMarta' && bucket.sanJose > 0)
    || (this.selectedBranch() !== 'sanJose' && bucket.santaMarta > 0)));

  protected readonly chartData = computed<ChartData<'bar'>>(() => {
    const datasets = [
      {
        label: 'San José',
        data: this.buckets().map((bucket) => bucket.sanJose),
        backgroundColor: '#2563eb',
        hoverBackgroundColor: '#1d4ed8',
        borderRadius: 4,
        maxBarThickness: 26,
      },
      {
        label: 'Santa Marta',
        data: this.buckets().map((bucket) => bucket.santaMarta),
        backgroundColor: '#ea580c',
        hoverBackgroundColor: '#c2410c',
        borderRadius: 4,
        maxBarThickness: 26,
      },
    ];
    const selected = this.selectedBranch();
    return {
      labels: this.buckets().map((bucket) => bucket.label),
      datasets: datasets.filter((_, index) => selected === 'all' || index === (selected === 'sanJose' ? 0 : 1)),
    };
  });

  protected readonly chartOptions = computed<ChartOptions<'bar'>>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 240 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: false,
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
          title: (items) => this.buckets()[items[0]?.dataIndex ?? 0]?.detail ?? items[0]?.label ?? '',
          label: (context) => ` ${context.dataset.label}: ${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(Number(context.parsed.y ?? 0))} gal`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: '#52636a', autoSkip: false, maxRotation: 45, minRotation: 45, font: { size: 10 } },
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
  }));
}

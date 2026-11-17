import { afterNextRender, ChangeDetectionStrategy, Component, effect, ElementRef, input, OnDestroy, viewChild } from '@angular/core';
import { BarController, BarElement, CategoryScale, Chart, LinearScale, Tooltip } from 'chart.js';

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip);

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-dashboard-chart', templateUrl: './dashboard-chart.html' })
export class DashboardChart implements OnDestroy {
  readonly title = input.required<string>();
  readonly labels = input.required<readonly string[]>();
  readonly values = input.required<readonly number[]>();
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart<'bar', number[], string> | undefined;

  constructor() {
    afterNextRender(() => {
      effect(() => {
        const labels = [...this.labels()];
        const values = [...this.values()];
        this.chart?.destroy();
        this.chart = new Chart(this.canvas().nativeElement, {
          type: 'bar',
          data: { labels, datasets: [{ data: values, backgroundColor: '#39c6ae', borderRadius: 6, maxBarThickness: 34 }] },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { enabled: true } }, scales: { y: { beginAtZero: true } } },
        });
      });
    });
  }

  ngOnDestroy(): void { this.chart?.destroy(); }
}

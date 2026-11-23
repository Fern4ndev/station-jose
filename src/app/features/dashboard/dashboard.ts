import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { UiIcon } from '../../shared/components/ui-icon/ui-icon';
import { UiPageHeading } from '../../shared/components/ui-page-heading/ui-page-heading';
import { AdminUiState } from '../../layouts/admin/admin-ui-state';
import { DashboardActivity } from './components/dashboard-activity/dashboard-activity';
import { DashboardMetrics } from './components/dashboard-metrics/dashboard-metrics';
import { DEMO_ATTENDANCES, visibleAttendances } from '../attendances/attendances-data';
import { buildDashboardMetrics } from './dashboard-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DashboardActivity, DashboardMetrics, UiIcon, UiPageHeading],
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  private readonly router = inject(Router);
  private readonly state = inject(AdminUiState);

  protected readonly role = this.state.role;
  protected readonly firstName = computed(() => this.state.user().name.split(' ')[0]);
  protected readonly today = new Intl.DateTimeFormat('es-PE', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date());

  protected readonly subtitle = computed(() =>
    this.role() === 'ATTENDANT'
      ? 'Consulta tus órdenes disponibles y registra cada despacho.'
      : 'Así se mueve la operación en tus dos sedes hoy.',
  );

  private readonly attendantName = computed(() =>
    this.role() === 'ATTENDANT' ? this.state.user().name : null,
  );

  protected readonly metrics = computed(() =>
    buildDashboardMetrics(this.attendantName(), this.state.branch()),
  );

  protected readonly recent = computed(() =>
    [
      ...visibleAttendances(DEMO_ATTENDANCES, this.attendantName(), this.state.branch()),
    ].reverse().slice(0, 4),
  );

  protected readonly scope = computed(() =>
    this.state.branch() === 'Todas las sedes' ? 'ambas sedes' : `la sede ${this.state.branch()}`,
  );

  protected goReports(): void {
    void this.router.navigateByUrl('/reportes');
  }

  protected goAttendances(): void {
    void this.router.navigateByUrl('/atenciones');
  }
}

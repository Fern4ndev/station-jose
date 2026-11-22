import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiPanel } from '../../../../shared/components/ui-panel/ui-panel';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../../attendances/attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon, UiPanel, UiStatusBadge],
  selector: 'app-dashboard-activity',
  templateUrl: './dashboard-activity.html',
})
export class DashboardActivity {
  readonly rows = input.required<readonly DemoAttendance[]>();
  readonly scope = input('ambas sedes');
  readonly viewAll = output<void>();

  protected gallons(value: number): string {
    return `${formatGallons(value)} gal`;
  }
}

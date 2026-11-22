import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiStatusBadge],
  selector: 'app-attendance-history',
  templateUrl: './attendance-history.html',
})
export class AttendanceHistory {
  readonly rows = input.required<readonly DemoAttendance[]>();

  protected gallons(row: DemoAttendance): string {
    return `${formatGallons(row.gallons)} gal`;
  }
}

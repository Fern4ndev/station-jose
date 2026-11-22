import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { UiIcon } from '../../../../shared/components/ui-icon/ui-icon';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../attendances-data';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon, UiStatusBadge],
  selector: 'app-attendance-recent',
  templateUrl: './attendance-recent.html',
})
export class AttendanceRecent {
  readonly rows = input.required<readonly DemoAttendance[]>();

  protected title(row: DemoAttendance): string {
    return `${row.voucher} · ${formatGallons(row.gallons)} gal`;
  }
}

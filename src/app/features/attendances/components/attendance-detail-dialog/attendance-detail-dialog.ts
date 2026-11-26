import { ChangeDetectionStrategy, Component, input, model } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import { UiStatusBadge } from '../../../../shared/components/ui-status-badge/ui-status-badge';
import { formatGallons } from '../../../orders/orders-data';
import type { DemoAttendance } from '../../attendances-data';

/** Detalle de una atención con uno o varios combustibles. */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiDialog, UiStatusBadge],
  selector: 'app-attendance-detail-dialog',
  templateUrl: './attendance-detail-dialog.html',
})
export class AttendanceDetailDialog {
  readonly visible = model(false);
  readonly attendance = input<DemoAttendance | null>(null);

  protected gallons(value: number | undefined): string {
    return value === undefined ? '—' : `${formatGallons(value)} gal`;
  }
}

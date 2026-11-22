import { ChangeDetectionStrategy, Component, input, model, output } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { DemoOrder } from '../../../orders/orders-data';
import type { DemoVoucher } from '../../../vouchers/vouchers-data';
import type { AttendanceRequest } from '../../attendances-data';
import { AttendanceForm } from '../attendance-form/attendance-form';

/** Formulario de despacho dentro de un modal, disparado desde la vista de atenciones. */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AttendanceForm, UiDialog],
  selector: 'app-attendance-form-dialog',
  templateUrl: './attendance-form-dialog.html',
})
export class AttendanceFormDialog {
  readonly visible = model(false);
  readonly orders = input.required<readonly DemoOrder[]>();
  readonly vouchers = input.required<readonly DemoVoucher[]>();
  readonly branch = input('San José');
  readonly branchLocked = input(false);
  readonly resetToken = input(0);

  readonly register = output<AttendanceRequest>();
}

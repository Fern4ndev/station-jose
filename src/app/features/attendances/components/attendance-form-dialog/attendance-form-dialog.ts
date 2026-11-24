import { ChangeDetectionStrategy, Component, input, model, output } from '@angular/core';
import { UiDialog } from '../../../../shared/components/ui-dialog/ui-dialog';
import type { AttendanceRequest } from '../../attendances-data';
import type { DispatchOrder, DispatchVoucher } from '../../operations-store';
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
  readonly orders = input.required<readonly DispatchOrder[]>();
  readonly vouchers = input.required<readonly DispatchVoucher[]>();
  readonly branch = input('San José');
  readonly branchLocked = input(false);
  readonly resetToken = input(0);

  readonly register = output<AttendanceRequest>();
}

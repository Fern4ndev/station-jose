import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { AttendanceLineDraft, AttendanceLineEditor } from '../attendance-line-editor/attendance-line-editor';

export type FirstAttendanceFormGroup = FormGroup<{
  issuerType: FormControl<'INSTITUTION' | 'STATION'>;
  issuerName: FormControl<string>;
  voucherNumber: FormControl<string>;
}>;

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [AttendanceLineEditor, ReactiveFormsModule], selector: 'app-first-attendance-form', templateUrl: './first-attendance-form.html' })
export class FirstAttendanceForm {
  readonly form = input.required<FirstAttendanceFormGroup>();
  readonly lines = input.required<readonly AttendanceLineDraft[]>();
  readonly submitting = input(false);
  readonly lineChange = output<AttendanceLineDraft>();
  readonly submitAttendance = output<void>();
}

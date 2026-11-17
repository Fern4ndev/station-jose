import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { AttendanceLineDraft, AttendanceLineEditor } from '../attendance-line-editor/attendance-line-editor';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [AttendanceLineEditor], selector: 'app-follow-up-attendance-form', templateUrl: './follow-up-attendance-form.html' })
export class FollowUpAttendanceForm {
  readonly voucherNumber = input.required<string>();
  readonly lines = input.required<readonly AttendanceLineDraft[]>();
  readonly submitting = input(false);
  readonly lineChange = output<AttendanceLineDraft>();
  readonly submitAttendance = output<void>();
}

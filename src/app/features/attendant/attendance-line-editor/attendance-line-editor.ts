import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface AttendanceLineDraft {
  readonly id: string;
  readonly fuelTypeName: string;
  readonly authorizedGallons: string;
  readonly attendedGallons: string;
  readonly availableGallons: string;
}

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-attendance-line-editor', templateUrl: './attendance-line-editor.html' })
export class AttendanceLineEditor {
  readonly lines = input.required<readonly AttendanceLineDraft[]>();
  readonly firstAttendance = input(false);
  readonly lineChange = output<AttendanceLineDraft>();

  protected update(line: AttendanceLineDraft, field: 'authorizedGallons' | 'attendedGallons', event: Event): void {
    const target = event.target;
    if (target instanceof HTMLInputElement) this.lineChange.emit({ ...line, [field]: target.value });
  }
}

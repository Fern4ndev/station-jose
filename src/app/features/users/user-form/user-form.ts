import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import type { BranchSummary, UserManagementRole } from '../../../core/models/auth.models';

export type UserFormGroup = FormGroup<{
  firstName: FormControl<string>;
  lastName: FormControl<string>;
  dni: FormControl<string>;
  email: FormControl<string>;
  password: FormControl<string>;
  role: FormControl<UserManagementRole>;
  branchId: FormControl<string>;
}>;

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReactiveFormsModule], selector: 'app-user-form', templateUrl: './user-form.html' })
export class UserForm {
  readonly form = input.required<UserFormGroup>();
  readonly branches = input<readonly BranchSummary[]>([]);
  readonly submitting = input(false);
  readonly enabled = input(false);
  readonly save = output<void>();
  readonly cancel = output<void>();
  protected canSubmit(): boolean {
    const form = this.form();
    return form.valid && (form.controls.role.value !== 'ATTENDANT' || form.controls.branchId.value.length > 0);
  }
}

import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';

export type VerificationFormGroup = FormGroup<{
  decision: FormControl<'VERIFIED' | 'OBSERVED'>;
  observation: FormControl<string>;
}>;

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReactiveFormsModule], selector: 'app-verification-form', templateUrl: './verification-form.html' })
export class VerificationForm {
  readonly form = input.required<VerificationFormGroup>();
  readonly submitting = input(false);
  readonly enabled = input(true);
  readonly submitDecision = output<void>();
  readonly cancel = output<void>();
  protected canSubmit(): boolean {
    const form = this.form();
    return form.valid && (form.controls.decision.value !== 'OBSERVED' || form.controls.observation.value.trim().length > 0);
  }
}

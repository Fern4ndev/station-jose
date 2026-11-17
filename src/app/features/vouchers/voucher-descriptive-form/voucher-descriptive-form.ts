import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';

export type VoucherDescriptiveFormGroup = FormGroup<{
  issuerType: FormControl<'INSTITUTION' | 'STATION'>;
  issuerName: FormControl<string>;
  voucherNumber: FormControl<string>;
}>;

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ReactiveFormsModule], selector: 'app-voucher-descriptive-form', templateUrl: './voucher-descriptive-form.html' })
export class VoucherDescriptiveForm {
  readonly form = input.required<VoucherDescriptiveFormGroup>();
  readonly submitting = input(false);
  readonly save = output<void>();
  readonly cancel = output<void>();
}

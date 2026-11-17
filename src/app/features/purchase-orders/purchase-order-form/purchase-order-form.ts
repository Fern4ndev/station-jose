import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { FuelLineDraft, FuelLineEditor, FuelTypeOption } from '../../../shared/components/fuel-line-editor/fuel-line-editor';
import { PdfUpload } from '../../../shared/components/pdf-upload/pdf-upload';
import type { BranchSummary } from '../../../core/models/auth.models';

export type PurchaseOrderFormGroup = FormGroup<{
  orderNumber: FormControl<string>;
  siafNumber: FormControl<string>;
  issueDate: FormControl<string>;
  institutionName: FormControl<string>;
  supplierName: FormControl<string>;
  supplierDetails: FormControl<string>;
  executingUnit: FormControl<string>;
  executingUnitRuc: FormControl<string>;
  branchId: FormControl<string>;
}>;

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [FuelLineEditor, PdfUpload, ReactiveFormsModule], selector: 'app-purchase-order-form', templateUrl: './purchase-order-form.html' })
export class PurchaseOrderForm {
  readonly form = input.required<PurchaseOrderFormGroup>();
  readonly lines = input.required<readonly FuelLineDraft[]>();
  readonly fuelTypes = input<readonly FuelTypeOption[]>([]);
  readonly branches = input<readonly BranchSummary[]>([]);
  readonly submitting = input(false);
  readonly lineChange = output<FuelLineDraft>();
  readonly lineAdd = output<void>();
  readonly lineRemove = output<string>();
  readonly pdfSelected = output<File>();
  readonly save = output<void>();
  readonly cancel = output<void>();
}

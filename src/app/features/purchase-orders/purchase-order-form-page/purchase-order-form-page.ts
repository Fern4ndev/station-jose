import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { FuelLineDraft } from '../../../shared/components/fuel-line-editor/fuel-line-editor';
import { PurchaseOrderForm } from '../purchase-order-form/purchase-order-form';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [PageHeader, PurchaseOrderForm, SectionPanel], selector: 'app-purchase-order-form-page', templateUrl: './purchase-order-form-page.html' })
export class PurchaseOrderFormPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  protected readonly lines = signal<readonly FuelLineDraft[]>([]);
  protected readonly form = this.fb.group({
    orderNumber: ['', Validators.required], siafNumber: ['', Validators.required], issueDate: ['', Validators.required],
    institutionName: ['', Validators.required], supplierName: ['', Validators.required], supplierDetails: [''],
    executingUnit: ['', Validators.required], executingUnitRuc: ['', Validators.required], branchId: ['', Validators.required],
  });
  protected addLine(): void { this.lines.update((lines) => [...lines, { id: crypto.randomUUID(), fuelTypeId: '', authorizedGallons: '', unitPrice: '', totalAmount: '' }]); }
  protected updateLine(updated: FuelLineDraft): void { this.lines.update((lines) => lines.map((line) => line.id === updated.id ? updated : line)); }
  protected removeLine(id: string): void { this.lines.update((lines) => lines.filter((line) => line.id !== id)); }
  protected cancel(): void { void this.router.navigate(['/app/purchase-orders']); }
}

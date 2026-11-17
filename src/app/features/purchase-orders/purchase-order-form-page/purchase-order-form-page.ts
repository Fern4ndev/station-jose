import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, forkJoin, of } from 'rxjs';
import { CatalogApi, CatalogItem } from '../../../core/services/catalog-api';
import { AuthStore } from '../../../core/services/auth/auth';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { FuelLineDraft } from '../../../shared/components/fuel-line-editor/fuel-line-editor';
import { PurchaseOrderForm } from '../purchase-order-form/purchase-order-form';
import { PurchaseOrderApi } from '../purchase-order-api';
import { OcrApi } from '../ocr-api';
import { OcrPreview, OcrPreviewResult, OcrPurchaseOrderCandidates } from '../ocr-preview/ocr-preview';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [OcrPreview, PageHeader, PurchaseOrderForm, SectionPanel], selector: 'app-purchase-order-form-page', templateUrl: './purchase-order-form-page.html' })
export class PurchaseOrderFormPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  private readonly api = inject(PurchaseOrderApi);
  private readonly catalog = inject(CatalogApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly ocr = inject(OcrApi);
  protected readonly auth = inject(AuthStore);
  private readonly orderId = inject(ActivatedRoute).snapshot.paramMap.get('orderId');
  protected readonly isEdit = this.orderId !== null;
  protected readonly preview = signal<OcrPreviewResult | null>(null);
  protected readonly processing = signal(false);
  protected readonly branches = signal<CatalogItem[]>([]);
  protected readonly fuels = signal<CatalogItem[]>([]);
  protected readonly catalogReady = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly lines = signal<readonly FuelLineDraft[]>([]);
  protected readonly form = this.fb.group({
    orderNumber: ['', Validators.required], siafNumber: ['', Validators.required], issueDate: ['', Validators.required],
    institutionName: ['', Validators.required], supplierName: ['', Validators.required], supplierDetails: [''],
    executingUnit: ['', Validators.required], executingUnitRuc: ['', Validators.required], branchId: ['', Validators.required],
  });
  constructor() { this.loadCatalogs(); }
  protected loadCatalogs(): void {
    this.catalogReady.set(false);
    this.error.set('');
    forkJoin({ branches: this.catalog.branches(), fuels: this.catalog.fuelTypes(), order: this.orderId ? this.api.get(this.orderId) : of(null) }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ({ branches, fuels, order }) => {
        this.branches.set(branches.filter((item) => item.is_active)); this.fuels.set(fuels.filter((item) => item.is_active));
        if (order) {
          this.form.setValue({ orderNumber: order.order_number, siafNumber: order.siaf_number, issueDate: order.issue_date, institutionName: order.institution_name, supplierName: order.supplier_name, supplierDetails: order.supplier_details ?? '', executingUnit: order.executing_unit, executingUnitRuc: order.executing_unit_ruc, branchId: order.branch.id });
          this.lines.set(order.items.map((item) => ({ id: item.id, fuelTypeId: item.fuel_type.id, authorizedGallons: item.authorized_gallons, unitPrice: item.unit_price, totalAmount: item.total_amount })));
        }
        this.catalogReady.set(true);
      },
      error: () => this.error.set('No se pudieron cargar la orden o sus catálogos.'),
    });
  }
  protected save(): void {
    if (this.saving() || this.form.invalid || !this.catalogReady()) { this.form.markAllAsTouched(); return; }
    const lines = this.lines();
    const decimal = /^\d+(?:\.\d{1,3})?$/;
    const price = /^\d+(?:\.\d{1,4})?$/;
    const amount = /^\d+(?:\.\d{1,2})?$/;
    if (!lines.length || new Set(lines.map((line) => line.fuelTypeId)).size !== lines.length || lines.some((line) => !line.fuelTypeId || !decimal.test(line.authorizedGallons) || Number(line.authorizedGallons) <= 0 || !price.test(line.unitPrice) || !amount.test(line.totalAmount))) {
      this.error.set('Revisa las líneas: selecciona combustibles distintos y completa cantidades, precios e importes válidos.'); return;
    }
    const value = this.form.getRawValue();
    this.error.set(''); this.saving.set(true);
    const request = { order_number: value.orderNumber.trim(), siaf_number: value.siafNumber.trim(), issue_date: value.issueDate,
      institution_name: value.institutionName.trim(), supplier_name: value.supplierName.trim(), supplier_details: value.supplierDetails.trim() || null,
      executing_unit: value.executingUnit.trim(), executing_unit_ruc: value.executingUnitRuc.trim(), branch_id: value.branchId,
      items: lines.map((line) => ({ fuel_type_id: line.fuelTypeId, authorized_gallons: line.authorizedGallons, unit_price: line.unitPrice, total_amount: line.totalAmount })),
    };
    const { order_number, ...updateRequest } = request;
    const operation = this.orderId ? this.api.update(this.orderId, updateRequest) : this.api.create({ order_number, ...updateRequest });
    operation.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: (order) => void this.router.navigate(['/app/purchase-orders', order.id]),
      error: (error: unknown) => this.error.set(error instanceof HttpErrorResponse && error.status === 409 ? 'La orden entra en conflicto con un registro existente.' : 'No se pudo guardar la orden. Revisa los datos e inténtalo de nuevo.'),
    });
  }
  protected processPdf(file: File): void {
    if (this.processing() || this.isEdit || !this.auth.hasPermission('ocr.purchase_orders.process')) return;
    this.error.set(''); this.preview.set(null); this.processing.set(true);
    this.ocr.preview(file).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.processing.set(false))).subscribe({
      next: (preview) => this.preview.set(preview),
      error: () => this.error.set('No se pudo procesar el PDF. Comprueba el archivo e inténtalo nuevamente.'),
    });
  }
  protected applyCandidates(fields: OcrPurchaseOrderCandidates): void {
    this.form.patchValue({ orderNumber: fields.orderNumber ?? '', siafNumber: fields.siafNumber ?? '', issueDate: fields.issueDate ?? '', institutionName: fields.institutionName ?? '', supplierName: fields.supplierName ?? '', executingUnit: fields.executingUnit ?? '', executingUnitRuc: fields.executingUnitRuc ?? '' });
    this.lines.set(fields.lines.map((line) => ({ id: crypto.randomUUID(), fuelTypeId: '', authorizedGallons: line.authorizedGallons ?? '', unitPrice: line.unitPrice ?? '', totalAmount: line.totalAmount ?? '' })));
    this.preview.set(null);
    if (fields.lines.length) this.error.set('Selecciona el combustible correspondiente a cada línea reconocida antes de guardar.');
  }
  protected addLine(): void { this.lines.update((lines) => [...lines, { id: crypto.randomUUID(), fuelTypeId: '', authorizedGallons: '', unitPrice: '', totalAmount: '' }]); }
  protected updateLine(updated: FuelLineDraft): void { this.lines.update((lines) => lines.map((line) => line.id === updated.id ? updated : line)); }
  protected removeLine(id: string): void { this.lines.update((lines) => lines.filter((line) => line.id !== id)); }
  protected cancel(): void { void this.router.navigate(['/app/purchase-orders']); }
}

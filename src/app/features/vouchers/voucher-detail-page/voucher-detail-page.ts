import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, Validators } from '@angular/forms';
import { AuthStore } from '../../../core/services/auth/auth';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ModalDelete } from '../../../shared/components/modal-delete/modal-delete';
import { PurchaseOrderApi } from '../../purchase-orders/purchase-order-api';
import { VoucherApi, VoucherDetail } from '../voucher-api';
import { finalize, forkJoin, of, switchMap } from 'rxjs';
import { VoucherDescriptiveForm } from '../voucher-descriptive-form/voucher-descriptive-form';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, ModalDelete, PageHeader, RouterLink, SectionPanel, VoucherDescriptiveForm], selector: 'app-voucher-detail-page', templateUrl: './voucher-detail-page.html' })
export class VoucherDetailPage {
  protected readonly voucherId = inject(ActivatedRoute).snapshot.paramMap.get('voucherId') ?? '';
  private readonly api = inject(VoucherApi);
  private readonly orders = inject(PurchaseOrderApi);
  protected readonly auth = inject(AuthStore);
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly state = signal<'loading' | 'error' | 'ready' | 'unavailable'>('loading');
  protected readonly voucher = signal<VoucherDetail | null>(null);
  protected readonly names = signal<ReadonlyMap<string, string>>(new Map());
  protected readonly editing = signal(false);
  protected readonly saving = signal(false);
  protected readonly deleting = signal(false);
  protected readonly confirmDelete = signal(false);
  protected readonly message = signal('');
  protected readonly success = signal('');
  protected readonly form = this.fb.group({ issuerType: ['INSTITUTION' as 'INSTITUTION' | 'STATION', Validators.required], issuerName: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(200)]], voucherNumber: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(60)]] });
  constructor() { this.load(); }
  protected load(): void {
    this.state.set('loading');
    this.api.get(this.voucherId).pipe(
      switchMap((voucher) => forkJoin({ voucher: of(voucher), order: this.orders.get(voucher.purchase_order_id) })),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({ voucher, order }) => {
        this.voucher.set(voucher);
        this.names.set(new Map(order.items.map((item) => [item.id, item.fuel_type.name])));
        this.state.set('ready');
      },
      error: () => this.state.set('error'),
    });
  }
  protected edit(): void {
    const voucher = this.voucher();
    if (!voucher || !this.auth.hasPermission('vouchers.correct_descriptive')) return;
    this.message.set(''); this.success.set('');
    this.form.setValue({ issuerType: voucher.issuer_type, issuerName: voucher.issuer_name, voucherNumber: voucher.voucher_number });
    this.editing.set(true);
  }
  protected save(): void {
    if (!this.auth.hasPermission('vouchers.correct_descriptive') || this.form.invalid || this.saving()) return;
    const value = this.form.getRawValue();
    this.saving.set(true); this.message.set(''); this.success.set('');
    this.api.correct(this.voucherId, { issuer_type: value.issuerType, issuer_name: value.issuerName.trim(), voucher_number: value.voucherNumber.trim() }).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: (voucher) => { this.voucher.set(voucher); this.editing.set(false); this.success.set('La corrección se guardó correctamente.'); },
      error: (error: unknown) => this.message.set(error instanceof HttpErrorResponse && error.status === 409 ? 'Ya existe un vale con esos datos en la orden.' : 'No se pudo guardar la corrección. Inténtalo nuevamente.'),
    });
  }
  protected delete(): void {
    if (!this.auth.hasPermission('vouchers.delete') || this.deleting()) return;
    this.deleting.set(true); this.message.set(''); this.success.set('');
    this.api.delete(this.voucherId).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.deleting.set(false))).subscribe({
      next: () => void this.router.navigate(['/app/vouchers']),
      error: (error: unknown) => this.message.set(error instanceof HttpErrorResponse && error.status === 409 ? 'No se puede eliminar un vale con atenciones registradas.' : 'No se pudo eliminar el vale. Inténtalo nuevamente.'),
    });
  }
}

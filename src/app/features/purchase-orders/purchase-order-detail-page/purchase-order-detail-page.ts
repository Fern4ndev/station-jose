import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { finalize } from 'rxjs';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PurchaseOrder, PurchaseOrderApi } from '../purchase-order-api';
import { AuthStore } from '../../../core/services/auth/auth';
import { ModalDelete } from '../../../shared/components/modal-delete/modal-delete';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, EmptyState, LoadingSkeleton, ModalDelete, PageHeader, RouterLink, SectionPanel], selector: 'app-purchase-order-detail-page', templateUrl: './purchase-order-detail-page.html' })
export class PurchaseOrderDetailPage {
  protected readonly orderId = inject(ActivatedRoute).snapshot.paramMap.get('orderId') ?? '';
  private readonly api = inject(PurchaseOrderApi);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  protected readonly confirmDelete = signal(false);
  protected readonly deleting = signal(false);
  protected readonly deleteError = signal('');
  protected readonly order = signal<PurchaseOrder | null>(null);
  protected readonly state = signal<'loading' | 'error' | 'ready' | 'unavailable'>('loading');
  constructor() { this.load(); }
  protected load(): void {
    this.state.set('loading');
    this.api.get(this.orderId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (order) => { this.order.set(order); this.state.set('ready'); },
      error: () => this.state.set('error'),
    });
  }
  protected delete(): void {
    if (this.deleting()) return;
    this.deleteError.set(''); this.deleting.set(true);
    this.api.delete(this.orderId).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.deleting.set(false))).subscribe({
      next: () => void this.router.navigate(['/purchase-orders']),
      error: (error: unknown) => this.deleteError.set(error instanceof HttpErrorResponse && error.status === 409 ? 'No se puede eliminar una orden con vales asociados.' : 'No se pudo eliminar la orden. Inténtalo de nuevo.'),
    });
  }
}

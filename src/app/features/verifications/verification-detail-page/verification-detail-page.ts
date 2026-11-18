import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { catchError, finalize, forkJoin, of, switchMap } from 'rxjs';
import { ApiError } from '../../../shared/components/api-error/api-error';
import { EmptyState } from '../../../shared/components/empty-state/empty-state';
import { LoadingSkeleton } from '../../../shared/components/loading-skeleton/loading-skeleton';
import { PageHeader } from '../../../shared/components/page-header/page-header';
import { SectionPanel } from '../../../shared/components/section-panel/section-panel';
import { VerificationForm } from '../verification-form/verification-form';
import { PendingVerification, VerificationApi, VerificationVoucher } from '../verification-api';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [ApiError, DatePipe, EmptyState, LoadingSkeleton, PageHeader, RouterLink, SectionPanel, VerificationForm], selector: 'app-verification-detail-page', templateUrl: './verification-detail-page.html' })
export class VerificationDetailPage {
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly api = inject(VerificationApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  protected readonly attendanceId = inject(ActivatedRoute).snapshot.paramMap.get('attendanceId') ?? '';
  protected readonly pending = signal<PendingVerification | null>(null);
  protected readonly attendance = signal<VerificationVoucher['attendances'][number] | null>(null);
  protected readonly orderNumber = signal('');
  protected readonly lines = signal<readonly { readonly id: string; readonly name: string; readonly gallons: string }[]>([]);
  protected readonly state = signal<'loading' | 'error' | 'missing' | 'ready'>('loading');
  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly form = this.fb.group({
    decision: ['VERIFIED' as 'VERIFIED' | 'OBSERVED', Validators.required],
    observation: [''],
  });

  constructor() { this.load(); }

  protected load(): void {
    this.state.set('loading');
    this.api.pending().pipe(
      switchMap((rows) => {
        const row = rows.find((item) => item.attendance_id === this.attendanceId);
        this.pending.set(row ?? null);
        return row ? forkJoin({ voucher: this.api.voucher(row.voucher_id), order: this.api.order(row.purchase_order_id) }) : of(null);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        const attendance = result?.voucher.attendances.find((item) => item.id === this.attendanceId) ?? null;
        this.orderNumber.set(result?.order.order_number ?? '');
        const lines = attendance?.items.map((line) => {
          const voucherLine = result?.voucher.items.find((item) => item.id === line.voucher_item_id);
          const orderLine = result?.order.items.find((item) => item.id === voucherLine?.purchase_order_item_id);
          return { id: line.id, name: orderLine?.fuel_type.name ?? '', gallons: line.attended_gallons };
        }) ?? [];
        this.lines.set(lines);
        this.attendance.set(attendance);
        this.state.set(attendance && lines.length && lines.every((line) => line.name) ? 'ready' : 'missing');
      },
      error: () => this.state.set('error'),
    });
  }

  protected submit(): void {
    const { decision, observation } = this.form.getRawValue();
    if (this.submitting() || this.state() !== 'ready' || (decision === 'OBSERVED' && !observation.trim())) return;
    this.errorMessage.set('');
    this.submitting.set(true);
    this.api.verify(this.attendanceId, { decision, observation: observation.trim() || null }).pipe(
      takeUntilDestroyed(this.destroyRef),
      catchError((error: unknown) => {
        this.errorMessage.set(error instanceof HttpErrorResponse && error.status === 409
          ? 'La atención ya fue verificada. Actualiza la bandeja para consultar su estado.'
          : 'No se pudo registrar la revisión. Inténtalo nuevamente.');
        return of(null);
      }),
      finalize(() => this.submitting.set(false)),
    ).subscribe((response) => {
      if (response) void this.router.navigate(['/attendances/pending-verification'], { queryParams: { reviewed: '1' } });
    });
  }

  protected cancel(): void { void this.router.navigate(['/attendances/pending-verification']); }
}

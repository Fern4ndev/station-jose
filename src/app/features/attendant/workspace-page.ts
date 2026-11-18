import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { catchError, finalize, forkJoin, map, Observable, of, Subject, switchMap } from 'rxjs';
import { EmptyState } from '../../shared/components/empty-state/empty-state';
import { PageHeader } from '../../shared/components/page-header/page-header';
import { SectionPanel } from '../../shared/components/section-panel/section-panel';
import type { AttendanceLineDraft } from './attendance-line-editor/attendance-line-editor';
import { FirstAttendanceForm } from './first-attendance-form/first-attendance-form';
import type { FirstAttendanceFormGroup } from './first-attendance-form/first-attendance-form';
import { FollowUpAttendanceForm } from './follow-up-attendance-form/follow-up-attendance-form';
import { OrderSearch } from './order-search/order-search';
import { VoucherSearch } from './voucher-search/voucher-search';
import { AttendanceApi } from './attendance-api';
import type { AttendanceCreated, FirstAttendanceRequest, FollowUpAttendanceRequest } from './attendance-api';
import { PurchaseOrderApi } from '../purchase-orders/purchase-order-api';
import type { PurchaseOrder } from '../purchase-orders/purchase-order-api';
import { VoucherApi } from '../vouchers/voucher-api';
import type { VoucherDetail } from '../vouchers/voucher-api';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState, FirstAttendanceForm, FollowUpAttendanceForm, OrderSearch, PageHeader, RouterLink, SectionPanel, VoucherSearch],
  selector: 'app-attendant-workspace-page',
  styleUrl: './workspace-page.css',
  templateUrl: './workspace-page.html',
})
export class WorkspacePage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly ordersApi = inject(PurchaseOrderApi);
  private readonly vouchersApi = inject(VoucherApi);
  private readonly attendanceApi = inject(AttendanceApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  private readonly orderQueries = new Subject<string>();
  private readonly voucherQueries = new Subject<string>();
  private readonly orderId = this.route.snapshot.paramMap.get('orderId') ?? '';
  private readonly voucherId = this.route.snapshot.paramMap.get('voucherId') ?? '';

  protected readonly hasOrder = this.orderId.length > 0;
  protected readonly hasVoucher = this.voucherId.length > 0;
  protected readonly title = String(this.route.snapshot.data['title'] ?? 'Espacio de atención');
  protected readonly description = String(this.route.snapshot.data['description'] ?? 'Consulta órdenes y vales para registrar un despacho.');
  protected readonly orders = signal<readonly PurchaseOrder[]>([]);
  protected readonly vouchers = signal<readonly VoucherDetail[]>([]);
  protected readonly orderState = signal<'initial' | 'loading' | 'ready' | 'error'>('initial');
  protected readonly voucherState = signal<'initial' | 'loading' | 'ready' | 'error'>('initial');
  protected readonly selectionState = signal<'loading' | 'ready' | 'error'>(this.orderId || this.voucherId ? 'loading' : 'ready');
  protected readonly selectedOrder = signal<PurchaseOrder | null>(null);
  protected readonly selectedVoucher = signal<VoucherDetail | null>(null);
  protected readonly firstLines = signal<readonly AttendanceLineDraft[]>([]);
  protected readonly followUpLines = signal<readonly AttendanceLineDraft[]>([]);
  protected readonly saving = signal(false);
  protected readonly submitError = signal('');
  protected readonly firstForm: FirstAttendanceFormGroup = this.formBuilder.group({
    issuerType: ['INSTITUTION' as 'INSTITUTION' | 'STATION', Validators.required],
    issuerName: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(200)]],
    voucherNumber: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(60)]],
  });

  constructor() {
    this.orderQueries
      .pipe(
        switchMap((query) => {
          if (query.length < 2) return of({ state: 'initial' as const, items: [] as readonly PurchaseOrder[] });
          this.orderState.set('loading');
          return this.ordersApi.search(query).pipe(
            map((result) => ({ state: 'ready' as const, items: result.items })),
            catchError(() => of({ state: 'error' as const, items: [] as readonly PurchaseOrder[] })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ state, items }) => {
        this.orders.set(items);
        this.orderState.set(state);
      });

    this.voucherQueries
      .pipe(
        switchMap((query) => {
          if (query.length < 2) return of({ state: 'initial' as const, items: [] as readonly VoucherDetail[] });
          this.voucherState.set('loading');
          return this.vouchersApi.search(query).pipe(
            map((result) => ({ state: 'ready' as const, items: result.items })),
            catchError(() => of({ state: 'error' as const, items: [] as readonly VoucherDetail[] })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ state, items }) => {
        this.vouchers.set(items);
        this.voucherState.set(state);
      });

    if (this.orderId) this.loadOrder(this.orderId);
    if (this.voucherId) this.loadVoucher(this.voucherId);
  }

  protected searchOrders(query: string): void {
    this.orderQueries.next(query.trim());
  }

  protected searchVouchers(query: string): void {
    this.voucherQueries.next(query.trim());
  }

  protected updateFirstLine(updated: AttendanceLineDraft): void {
    this.firstLines.update((lines) => lines.map((line) => line.id === updated.id ? updated : line));
  }

  protected updateFollowUpLine(updated: AttendanceLineDraft): void {
    this.followUpLines.update((lines) => lines.map((line) => line.id === updated.id ? updated : line));
  }

  protected registerFirstAttendance(): void {
    if (this.saving()) return;
    if (this.firstForm.invalid) {
      this.firstForm.markAllAsTouched();
      return;
    }

    const order = this.selectedOrder();
    if (!order) return;
    const lines = this.firstLines();
    if (!this.hasValidFirstLines(lines)) {
      this.submitError.set('Ingresa autorización y galones despachados válidos. El despacho no puede superar los saldos de la orden ni del vale.');
      return;
    }

    const value = this.firstForm.getRawValue();
    const request: FirstAttendanceRequest = {
      issuer_type: value.issuerType,
      issuer_name: value.issuerName.trim(),
      voucher_number: value.voucherNumber.trim(),
      voucher_items: lines
        .filter((line) => this.isPositiveAmount(line.authorizedGallons))
        .map((line) => ({ purchase_order_item_id: line.id, authorized_gallons: line.authorizedGallons })),
      items: lines
        .filter((line) => this.isPositiveAmount(line.attendedGallons))
        .map((line) => ({ purchase_order_item_id: line.id, attended_gallons: line.attendedGallons })),
    };
    this.submit(this.attendanceApi.createFirst(order.id, request));
  }

  protected registerFollowUpAttendance(): void {
    if (this.saving()) return;
    const voucher = this.selectedVoucher();
    if (!voucher) return;
    const lines = this.followUpLines();
    if (!this.hasValidFollowUpLines(lines)) {
      this.submitError.set('Ingresa los galones de esta atención sin superar el saldo disponible del vale.');
      return;
    }

    const request: FollowUpAttendanceRequest = {
      items: lines
        .filter((line) => this.isPositiveAmount(line.attendedGallons))
        .map((line) => ({ voucher_item_id: line.id, attended_gallons: line.attendedGallons })),
    };
    this.submit(this.attendanceApi.createFollowUp(voucher.id, request));
  }

  private loadOrder(orderId: string): void {
    this.ordersApi.get(orderId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (order) => {
        this.selectedOrder.set(order);
        this.firstLines.set(order.items.map((item) => ({
          id: item.id,
          fuelTypeName: item.fuel_type.name,
          authorizedGallons: '',
          attendedGallons: '',
          availableGallons: item.available_gallons,
        })));
        this.selectionState.set('ready');
      },
      error: () => this.selectionState.set('error'),
    });
  }

  private loadVoucher(voucherId: string): void {
    this.vouchersApi.get(voucherId)
      .pipe(
        switchMap((voucher) => forkJoin({ voucher: of(voucher), order: this.ordersApi.get(voucher.purchase_order_id) })),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ voucher, order }) => {
          const fuelNames = new Map(order.items.map((item) => [item.id, item.fuel_type.name]));
          this.selectedVoucher.set(voucher);
          this.followUpLines.set(voucher.items.map((item) => ({
            id: item.id,
            fuelTypeName: fuelNames.get(item.purchase_order_item_id) ?? 'Combustible',
            authorizedGallons: item.authorized_gallons,
            attendedGallons: '',
            availableGallons: item.available_gallons,
          })));
          this.selectionState.set('ready');
        },
        error: () => this.selectionState.set('error'),
      });
  }

  private submit(request: Observable<AttendanceCreated>): void {
    this.submitError.set('');
    this.saving.set(true);
    request
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => void this.router.navigate(['/attendant/attendances'], { queryParams: { registered: '1' } }),
        error: (error: unknown) => this.submitError.set(this.apiErrorMessage(error)),
      });
  }

  private hasValidFirstLines(lines: readonly AttendanceLineDraft[]): boolean {
    const authorized = lines.filter((line) => this.isPositiveAmount(line.authorizedGallons));
    const attended = lines.filter((line) => this.isPositiveAmount(line.attendedGallons));
    if (!authorized.length || !attended.length) return false;

    return lines.every((line) => {
      const authorizedGallons = Number(line.authorizedGallons || 0);
      const attendedGallons = Number(line.attendedGallons || 0);
      const availableGallons = Number(line.availableGallons);
      if (line.authorizedGallons && !this.isPositiveAmount(line.authorizedGallons)) return false;
      if (line.attendedGallons && !this.isPositiveAmount(line.attendedGallons)) return false;
      if (attendedGallons > 0 && authorizedGallons <= 0) return false;
      return authorizedGallons <= availableGallons && attendedGallons <= authorizedGallons;
    });
  }

  private hasValidFollowUpLines(lines: readonly AttendanceLineDraft[]): boolean {
    const attended = lines.filter((line) => this.isPositiveAmount(line.attendedGallons));
    if (!attended.length) return false;
    return lines.every((line) => {
      const attendedGallons = Number(line.attendedGallons || 0);
      if (line.attendedGallons && !this.isPositiveAmount(line.attendedGallons)) return false;
      return attendedGallons <= Number(line.availableGallons);
    });
  }

  private isPositiveAmount(value: string): boolean {
    return /^\d+(?:\.\d{1,3})?$/.test(value) && Number(value) > 0;
  }

  private apiErrorMessage(error: unknown): string {
    const message: unknown = error instanceof HttpErrorResponse ? error.error?.error?.message : null;
    return typeof message === 'string' && message
      ? message
      : 'No se pudo registrar el despacho. Revisa los datos e inténtalo nuevamente.';
  }
}

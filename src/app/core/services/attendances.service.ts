import { HttpHeaders } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi, apiUrl } from '../api/api-url';
import { API_ENDPOINTS, IDEMPOTENCY_HEADER } from '../api/endpoints';
import type {
  AttendanceResult,
  FirstAttendanceCreate,
  FollowUpAttendanceCreate,
} from '../models/attendance.model';

/** Atenciones: creación de la primera y de las siguientes sobre un vale. */
@Injectable({ providedIn: 'root' })
export class AttendancesService extends BaseApi {
  private readonly submittingState = signal(false);
  private readonly lastResultState = signal<AttendanceResult | null>(null);

  readonly submitting = this.submittingState.asReadonly();
  readonly lastResult = this.lastResultState.asReadonly();

  /** Primera atención de la orden: crea el vale con su autorización. */
  createFirst(
    orderId: string,
    payload: FirstAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.send(API_ENDPOINTS.purchaseOrders.attendances(orderId), payload, idempotencyKey);
  }

  /** Atenciones siguientes sobre un vale ya emitido. */
  createFollowUp(
    voucherId: string,
    payload: FollowUpAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.send(API_ENDPOINTS.vouchers.attendances(voucherId), payload, idempotencyKey);
  }

  private send<TBody>(
    path: string,
    payload: TBody,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    this.submittingState.set(true);
    return this.http
      .post<AttendanceResult>(apiUrl(path), payload, {
        headers: new HttpHeaders({ [IDEMPOTENCY_HEADER]: idempotencyKey }),
      })
      .pipe(
        tap((result) => this.lastResultState.set(result)),
        finalize(() => this.submittingState.set(false)),
      );
  }
}

import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS, IDEMPOTENCY_HEADER } from '../api/endpoints';
import type {
  AttendanceResult,
  FirstAttendanceCreate,
  FollowUpAttendanceCreate,
} from '../models/attendance';

/** Atenciones: primera atención de la orden y siguientes sobre un vale. */
@Injectable({ providedIn: 'root' })
export class AttendancesApi extends BaseApi {
  /** Primera atención de la orden: crea el vale con su autorización. */
  createFirst(
    orderId: string,
    payload: FirstAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.send(
      API_ENDPOINTS.purchaseOrders.attendances(orderId),
      payload,
      idempotencyKey,
    );
  }

  /** Atenciones siguientes sobre un vale ya emitido. */
  createFollowUp(
    voucherId: string,
    payload: FollowUpAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.send(
      API_ENDPOINTS.vouchers.attendances(voucherId),
      payload,
      idempotencyKey,
    );
  }

  private send<TBody>(
    path: string,
    payload: TBody,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.postWithHeaders<AttendanceResult>(path, payload, {
      [IDEMPOTENCY_HEADER]: idempotencyKey,
    });
  }
}

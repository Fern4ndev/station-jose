import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi, IDEMPOTENCY_HEADER } from '../api/api-url';
import type {
  AttendanceResult,
  FirstAttendanceCreate,
  FollowUpAttendanceCreate,
} from '../models/attendance';
import type { PaginatedResponse } from '../models/pagination';

/** Atenciones: primera atención de la orden y siguientes sobre un vale. */
@Injectable({ providedIn: 'root' })
export class AttendancesApi extends BaseApi {
  list(query: { page?: number; page_size?: number } = {}): Observable<PaginatedResponse<AttendanceResult>> {
    return this.get<PaginatedResponse<AttendanceResult>>(API_ENDPOINTS.attendances.base, query);
  }

  detail(attendanceId: string): Observable<AttendanceResult> {
    return this.get<AttendanceResult>(API_ENDPOINTS.attendances.byId(attendanceId));
  }

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

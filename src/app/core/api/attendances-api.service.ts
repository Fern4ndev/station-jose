import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS, IDEMPOTENCY_HEADER } from '../constants/api.constants';
import type {
  AttendanceResult,
  FirstAttendanceCreate,
  FollowUpAttendanceCreate,
} from '../models/attendance.model';

@Injectable({ providedIn: 'root' })
export class AttendancesApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  /** Primera atención de la orden: crea el vale con su autorización. */
  createFirst(
    orderId: string,
    payload: FirstAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.http.post<AttendanceResult>(
      `${this.baseUrl}${API_ENDPOINTS.purchaseOrders.attendances(orderId)}`,
      payload,
      { headers: this.idempotencyHeaders(idempotencyKey) },
    );
  }

  /** Atenciones siguientes sobre un vale ya emitido. */
  createFollowUp(
    voucherId: string,
    payload: FollowUpAttendanceCreate,
    idempotencyKey: string,
  ): Observable<AttendanceResult> {
    return this.http.post<AttendanceResult>(
      `${this.baseUrl}${API_ENDPOINTS.vouchers.attendances(voucherId)}`,
      payload,
      { headers: this.idempotencyHeaders(idempotencyKey) },
    );
  }

  private idempotencyHeaders(idempotencyKey: string): HttpHeaders {
    return new HttpHeaders({ [IDEMPOTENCY_HEADER]: idempotencyKey });
  }
}

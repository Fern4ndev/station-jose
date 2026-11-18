import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface FirstAttendanceRequest {
  readonly issuer_type: 'INSTITUTION' | 'STATION';
  readonly issuer_name: string;
  readonly voucher_number: string;
  readonly voucher_items: readonly {
    readonly purchase_order_item_id: string;
    readonly authorized_gallons: string;
  }[];
  readonly items: readonly {
    readonly purchase_order_item_id: string;
    readonly attended_gallons: string;
  }[];
}

export interface FollowUpAttendanceRequest {
  readonly items: readonly {
    readonly voucher_item_id: string;
    readonly attended_gallons: string;
  }[];
}

export interface AttendanceCreated {
  readonly id: string;
  readonly voucher_id: string;
}

@Injectable({ providedIn: 'root' })
export class AttendanceApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  createFirst(orderId: string, request: FirstAttendanceRequest): Observable<AttendanceCreated> {
    return this.http.post<AttendanceCreated>(
      `${this.baseUrl}/purchase-orders/${encodeURIComponent(orderId)}/attendances`,
      request,
      { headers: this.idempotencyHeaders() },
    );
  }

  createFollowUp(voucherId: string, request: FollowUpAttendanceRequest): Observable<AttendanceCreated> {
    return this.http.post<AttendanceCreated>(
      `${this.baseUrl}/vouchers/${encodeURIComponent(voucherId)}/attendances`,
      request,
      { headers: this.idempotencyHeaders() },
    );
  }

  private idempotencyHeaders(): HttpHeaders {
    return new HttpHeaders({ 'Idempotency-Key': crypto.randomUUID() });
  }
}

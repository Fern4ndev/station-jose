import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface PendingVerification {
  readonly attendance_id: string;
  readonly voucher_id: string;
  readonly purchase_order_id: string;
  readonly voucher_number: string;
  readonly issuer_name: string;
  readonly performed_by_user_id: string;
  readonly branch_id: string;
  readonly attended_at: string;
  readonly verification_status: string;
}

export interface VerificationRequest {
  readonly decision: 'VERIFIED' | 'OBSERVED';
  readonly observation: string | null;
}

export interface VerificationVoucher {
  readonly items: readonly { readonly id: string; readonly purchase_order_item_id: string }[];
  readonly attendances: readonly {
    readonly id: string;
    readonly items: readonly { readonly id: string; readonly voucher_item_id: string; readonly attended_gallons: string }[];
  }[];
}

export interface VerificationOrder {
  readonly order_number: string;
  readonly items: readonly { readonly id: string; readonly fuel_type: { readonly name: string } }[];
}

@Injectable({ providedIn: 'root' })
export class VerificationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  pending(): Observable<PendingVerification[]> {
    return this.http.get<PendingVerification[]>(`${this.baseUrl}/verifications/pending`);
  }

  voucher(voucherId: string): Observable<VerificationVoucher> {
    return this.http.get<VerificationVoucher>(`${this.baseUrl}/vouchers/${encodeURIComponent(voucherId)}`);
  }

  order(orderId: string): Observable<VerificationOrder> {
    return this.http.get<VerificationOrder>(`${this.baseUrl}/purchase-orders/${encodeURIComponent(orderId)}`);
  }

  verify(attendanceId: string, request: VerificationRequest): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/attendances/${encodeURIComponent(attendanceId)}/verifications`, request);
  }
}

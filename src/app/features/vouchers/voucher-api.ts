import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface VoucherDetail {
  readonly id: string;
  readonly voucher_number: string;
  readonly issuer_type: 'INSTITUTION' | 'STATION';
  readonly issuer_name: string;
  readonly created_at: string;
  readonly status: string;
  readonly verification_status: string;
  readonly items: readonly { readonly id: string; readonly purchase_order_item_id: string; readonly authorized_gallons: string; readonly attended_gallons: string; readonly available_gallons: string }[];
  readonly purchase_order_id: string;
  readonly attendances: readonly { readonly id: string; readonly attended_at: string; readonly items: readonly { readonly id: string; readonly attended_gallons: string }[]; readonly verifications: readonly { readonly id: string; readonly decision: string; readonly observation: string | null; readonly reviewed_at: string }[] }[];
}

@Injectable({ providedIn: 'root' })
export class VoucherApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);
  get(id: string): Observable<VoucherDetail> {
    return this.http.get<VoucherDetail>(`${this.baseUrl}/vouchers/${encodeURIComponent(id)}`);
  }
  search(number: string, page = 1): Observable<{ readonly items: readonly VoucherDetail[]; readonly pagination: { readonly page: number; readonly pages: number } }> {
    return this.http.get<{ readonly items: readonly VoucherDetail[]; readonly pagination: { readonly page: number; readonly pages: number } }>(`${this.baseUrl}/vouchers`, {
      params: new HttpParams().set('voucher_number', number).set('page', page).set('page_size', 20),
    });
  }
  correct(id: string, request: { issuer_type: 'INSTITUTION' | 'STATION'; issuer_name: string; voucher_number: string }): Observable<VoucherDetail> {
    return this.http.patch<VoucherDetail>(`${this.baseUrl}/vouchers/${encodeURIComponent(id)}/descriptive-data`, request);
  }
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/vouchers/${encodeURIComponent(id)}`);
  }
}

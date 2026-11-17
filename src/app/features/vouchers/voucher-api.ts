import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface VoucherDetail {
  readonly id: string;
  readonly voucher_number: string;
  readonly issuer_name: string;
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
}

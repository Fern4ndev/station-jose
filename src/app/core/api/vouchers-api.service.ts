import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type {
  AttendedVoucherQuery,
  OperationalVoucherList,
  VoucherDescriptiveUpdate,
  VoucherDetail,
  VoucherListResponse,
  VoucherQuery,
  VoucherResponse,
} from '../models/voucher.model';
import { toHttpParams } from './http-params';

@Injectable({ providedIn: 'root' })
export class VouchersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  list(query: VoucherQuery = {}): Observable<VoucherListResponse | OperationalVoucherList> {
    return this.http.get<VoucherListResponse | OperationalVoucherList>(
      `${this.baseUrl}${API_ENDPOINTS.vouchers.base}`,
      { params: toHttpParams(query) },
    );
  }

  attended(query: AttendedVoucherQuery = {}): Observable<OperationalVoucherList> {
    return this.http.get<OperationalVoucherList>(
      `${this.baseUrl}${API_ENDPOINTS.vouchers.attended}`,
      { params: toHttpParams(query) },
    );
  }

  get(voucherId: string): Observable<VoucherDetail> {
    return this.http.get<VoucherDetail>(
      `${this.baseUrl}${API_ENDPOINTS.vouchers.byId(voucherId)}`,
    );
  }

  remove(voucherId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}${API_ENDPOINTS.vouchers.byId(voucherId)}`);
  }

  correctDescriptive(
    voucherId: string,
    payload: VoucherDescriptiveUpdate,
  ): Observable<VoucherResponse> {
    return this.http.patch<VoucherResponse>(
      `${this.baseUrl}${API_ENDPOINTS.vouchers.descriptiveData(voucherId)}`,
      payload,
    );
  }
}

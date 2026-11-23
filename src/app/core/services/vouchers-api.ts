import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';
import type {
  AttendedVoucherQuery,
  OperationalVoucherList,
  VoucherDescriptiveUpdate,
  VoucherDetail,
  VoucherListResponse,
  VoucherQuery,
  VoucherResponse,
} from '../models/voucher';

/** Vales: listados, detalle, corrección descriptiva y borrado. */
@Injectable({ providedIn: 'root' })
export class VouchersApi extends BaseApi {
  list(query: VoucherQuery = {}): Observable<VoucherListResponse | OperationalVoucherList> {
    return this.get<VoucherListResponse | OperationalVoucherList>(
      API_ENDPOINTS.vouchers.base,
      query,
    );
  }

  attended(query: AttendedVoucherQuery = {}): Observable<OperationalVoucherList> {
    return this.get<OperationalVoucherList>(API_ENDPOINTS.vouchers.attended, query);
  }

  detail(voucherId: string): Observable<VoucherDetail> {
    return this.get<VoucherDetail>(API_ENDPOINTS.vouchers.byId(voucherId));
  }

  remove(voucherId: string): Observable<void> {
    return this.delete<void>(API_ENDPOINTS.vouchers.byId(voucherId));
  }

  correctDescriptive(
    voucherId: string,
    payload: VoucherDescriptiveUpdate,
  ): Observable<VoucherResponse> {
    return this.patch<VoucherResponse>(
      API_ENDPOINTS.vouchers.descriptiveData(voucherId),
      payload,
    );
  }
}

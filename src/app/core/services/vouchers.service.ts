import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  AttendedVoucherQuery,
  OperationalVoucher,
  OperationalVoucherList,
  VoucherDescriptiveUpdate,
  VoucherDetail,
  VoucherListResponse,
  VoucherQuery,
  VoucherResponse,
} from '../models/voucher.model';

type VoucherListItem = VoucherResponse | OperationalVoucher;

/** Vales: listados, detalle, corrección descriptiva y borrado. */
@Injectable({ providedIn: 'root' })
export class VouchersService extends BaseApi {
  private readonly loadingState = signal(false);
  private readonly itemsState = signal<readonly VoucherListItem[]>([]);
  private readonly totalState = signal(0);
  private readonly selectedState = signal<VoucherDetail | null>(null);

  readonly loading = this.loadingState.asReadonly();
  readonly vouchers = this.itemsState.asReadonly();
  readonly total = this.totalState.asReadonly();
  readonly selected = this.selectedState.asReadonly();

  list(query: VoucherQuery = {}): Observable<VoucherListResponse | OperationalVoucherList> {
    this.loadingState.set(true);
    return this.get<VoucherListResponse | OperationalVoucherList>(
      API_ENDPOINTS.vouchers.base,
      query,
    ).pipe(
      tap((response) => {
        this.itemsState.set(response.items);
        this.totalState.set(response.pagination.total);
      }),
      finalize(() => this.loadingState.set(false)),
    );
  }

  attended(query: AttendedVoucherQuery = {}): Observable<OperationalVoucherList> {
    this.loadingState.set(true);
    return this.get<OperationalVoucherList>(API_ENDPOINTS.vouchers.attended, query).pipe(
      tap((response) => {
        this.itemsState.set(response.items);
        this.totalState.set(response.pagination.total);
      }),
      finalize(() => this.loadingState.set(false)),
    );
  }

  detail(voucherId: string): Observable<VoucherDetail> {
    this.loadingState.set(true);
    return this.get<VoucherDetail>(API_ENDPOINTS.vouchers.byId(voucherId)).pipe(
      tap((voucher) => this.selectedState.set(voucher)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  remove(voucherId: string): Observable<void> {
    return this.delete<void>(API_ENDPOINTS.vouchers.byId(voucherId)).pipe(
      tap(() => {
        this.itemsState.update((vouchers) =>
          vouchers.filter((voucher) => voucher.id !== voucherId),
        );
        this.totalState.update((total) => Math.max(0, total - 1));
        if (this.selectedState()?.id === voucherId) {
          this.selectedState.set(null);
        }
      }),
    );
  }

  correctDescriptive(
    voucherId: string,
    payload: VoucherDescriptiveUpdate,
  ): Observable<VoucherResponse> {
    return this.patch<VoucherResponse>(
      API_ENDPOINTS.vouchers.descriptiveData(voucherId),
      payload,
    ).pipe(
      tap((voucher) => {
        this.itemsState.update((vouchers) =>
          vouchers.map((item) => (item.id === voucher.id ? voucher : item)),
        );
        if (this.selectedState()?.id === voucher.id) {
          this.selectedState.set(voucher);
        }
      }),
    );
  }
}

import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  OperationalOrder,
  OperationalOrderList,
  PurchaseOrderCreate,
  PurchaseOrderDetail,
  PurchaseOrderListResponse,
  PurchaseOrderQuery,
  PurchaseOrderResponse,
  PurchaseOrderUpdate,
} from '../models/purchase-order.model';

type OrderListItem = PurchaseOrderResponse | OperationalOrder;

/** Órdenes de compra: CRUD completo y caché reactiva del listado vigente. */
@Injectable({ providedIn: 'root' })
export class PurchaseOrdersService extends BaseApi {
  private readonly loadingState = signal(false);
  private readonly itemsState = signal<readonly OrderListItem[]>([]);
  private readonly totalState = signal(0);
  private readonly selectedState = signal<PurchaseOrderDetail | null>(null);

  readonly loading = this.loadingState.asReadonly();
  readonly orders = this.itemsState.asReadonly();
  readonly total = this.totalState.asReadonly();
  readonly selected = this.selectedState.asReadonly();

  /** Respuesta reducida para ATTENDANT, completa para ADMIN/OFFICE. */
  list(
    query: PurchaseOrderQuery = {},
  ): Observable<PurchaseOrderListResponse | OperationalOrderList> {
    this.loadingState.set(true);
    return this.get<PurchaseOrderListResponse | OperationalOrderList>(
      API_ENDPOINTS.purchaseOrders.base,
      query,
    ).pipe(
      tap((response) => {
        this.itemsState.set(response.items);
        this.totalState.set(response.pagination.total);
      }),
      finalize(() => this.loadingState.set(false)),
    );
  }

  detail(orderId: string): Observable<PurchaseOrderDetail> {
    this.loadingState.set(true);
    return this.get<PurchaseOrderDetail>(API_ENDPOINTS.purchaseOrders.byId(orderId)).pipe(
      tap((order) => this.selectedState.set(order)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  create(payload: PurchaseOrderCreate): Observable<PurchaseOrderResponse> {
    return this.post<PurchaseOrderResponse>(API_ENDPOINTS.purchaseOrders.base, payload).pipe(
      tap((order) => {
        this.itemsState.update((orders) => [order, ...orders]);
        this.totalState.update((total) => total + 1);
      }),
    );
  }

  update(orderId: string, payload: PurchaseOrderUpdate): Observable<PurchaseOrderResponse> {
    return this.patch<PurchaseOrderResponse>(
      API_ENDPOINTS.purchaseOrders.byId(orderId),
      payload,
    ).pipe(tap((order) => this.sync(order)));
  }

  remove(orderId: string): Observable<void> {
    return this.delete<void>(API_ENDPOINTS.purchaseOrders.byId(orderId)).pipe(
      tap(() => {
        this.itemsState.update((orders) => orders.filter((order) => order.id !== orderId));
        this.totalState.update((total) => Math.max(0, total - 1));
        if (this.selectedState()?.id === orderId) {
          this.selectedState.set(null);
        }
      }),
    );
  }

  private sync(updated: PurchaseOrderResponse): void {
    this.itemsState.update((orders) =>
      orders.map((order) => (order.id === updated.id ? updated : order)),
    );
    if (this.selectedState()?.id === updated.id) {
      this.selectedState.set(updated);
    }
  }
}

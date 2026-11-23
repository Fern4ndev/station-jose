import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';
import type {
  OperationalOrderList,
  PurchaseOrderCreate,
  PurchaseOrderDetail,
  PurchaseOrderListResponse,
  PurchaseOrderQuery,
  PurchaseOrderResponse,
  PurchaseOrderUpdate,
} from '../models/purchase-order';

/** Órdenes de compra: CRUD completo. La vista decide qué hacer con la respuesta. */
@Injectable({ providedIn: 'root' })
export class PurchaseOrdersApi extends BaseApi {
  /** Respuesta reducida para ATTENDANT, completa para ADMIN/OFFICE. */
  list(
    query: PurchaseOrderQuery = {},
  ): Observable<PurchaseOrderListResponse | OperationalOrderList> {
    return this.get<PurchaseOrderListResponse | OperationalOrderList>(
      API_ENDPOINTS.purchaseOrders.base,
      query,
    );
  }

  detail(orderId: string): Observable<PurchaseOrderDetail> {
    return this.get<PurchaseOrderDetail>(API_ENDPOINTS.purchaseOrders.byId(orderId));
  }

  create(payload: PurchaseOrderCreate): Observable<PurchaseOrderResponse> {
    return this.post<PurchaseOrderResponse>(API_ENDPOINTS.purchaseOrders.base, payload);
  }

  update(orderId: string, payload: PurchaseOrderUpdate): Observable<PurchaseOrderResponse> {
    return this.patch<PurchaseOrderResponse>(
      API_ENDPOINTS.purchaseOrders.byId(orderId),
      payload,
    );
  }

  remove(orderId: string): Observable<void> {
    return this.delete<void>(API_ENDPOINTS.purchaseOrders.byId(orderId));
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type {
  OperationalOrderList,
  PurchaseOrderCreate,
  PurchaseOrderDetail,
  PurchaseOrderListResponse,
  PurchaseOrderQuery,
  PurchaseOrderResponse,
  PurchaseOrderUpdate,
} from '../models/purchase-order.model';
import { toHttpParams } from './http-params';

@Injectable({ providedIn: 'root' })
export class PurchaseOrdersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  /** Respuesta reducida para ATTENDANT, completa para ADMIN/OFFICE. */
  list(
    query: PurchaseOrderQuery = {},
  ): Observable<PurchaseOrderListResponse | OperationalOrderList> {
    return this.http.get<PurchaseOrderListResponse | OperationalOrderList>(
      `${this.baseUrl}${API_ENDPOINTS.purchaseOrders.base}`,
      { params: toHttpParams(query) },
    );
  }

  get(orderId: string): Observable<PurchaseOrderDetail> {
    return this.http.get<PurchaseOrderDetail>(
      `${this.baseUrl}${API_ENDPOINTS.purchaseOrders.byId(orderId)}`,
    );
  }

  create(payload: PurchaseOrderCreate): Observable<PurchaseOrderResponse> {
    return this.http.post<PurchaseOrderResponse>(
      `${this.baseUrl}${API_ENDPOINTS.purchaseOrders.base}`,
      payload,
    );
  }

  update(orderId: string, payload: PurchaseOrderUpdate): Observable<PurchaseOrderResponse> {
    return this.http.patch<PurchaseOrderResponse>(
      `${this.baseUrl}${API_ENDPOINTS.purchaseOrders.byId(orderId)}`,
      payload,
    );
  }

  remove(orderId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}${API_ENDPOINTS.purchaseOrders.byId(orderId)}`);
  }
}

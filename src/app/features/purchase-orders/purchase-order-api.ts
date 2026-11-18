import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface OrderItem {
  readonly id: string;
  readonly fuel_type: { readonly id: string; readonly name: string };
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
  readonly unit_price: string;
  readonly total_amount: string;
}

export interface PurchaseOrder {
  readonly id: string;
  readonly order_number: string;
  readonly siaf_number: string;
  readonly institution_name: string;
  readonly supplier_name: string;
  readonly supplier_details: string | null;
  readonly executing_unit: string;
  readonly executing_unit_ruc: string;
  readonly issue_date: string;
  readonly branch: { readonly id: string; readonly name: string };
  readonly status: string;
  readonly items: readonly OrderItem[];
}

export interface OrderPage {
  readonly items: readonly PurchaseOrder[];
  readonly pagination: { readonly page: number; readonly pages: number; readonly total: number };
}

export interface CreateOrderRequest {
  readonly order_number: string; readonly siaf_number: string; readonly issue_date: string;
  readonly institution_name: string; readonly supplier_name: string; readonly supplier_details: string | null;
  readonly executing_unit: string; readonly executing_unit_ruc: string; readonly branch_id: string;
  readonly items: readonly { readonly fuel_type_id: string; readonly authorized_gallons: string; readonly unit_price: string; readonly total_amount: string }[];
}

export interface OrderFilters {
  readonly branchId: string;
  readonly dateFrom: string;
  readonly dateTo: string;
  readonly sortBy: 'issue_date' | 'order_number' | 'institution_name';
  readonly sortOrder: 'asc' | 'desc';
}

@Injectable({ providedIn: 'root' })
export class PurchaseOrderApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  get(id: string): Observable<PurchaseOrder> {
    return this.http.get<PurchaseOrder>(`${this.baseUrl}/purchase-orders/${encodeURIComponent(id)}`);
  }

  create(request: CreateOrderRequest): Observable<PurchaseOrder> {
    return this.http.post<PurchaseOrder>(`${this.baseUrl}/purchase-orders`, request);
  }

  update(id: string, request: Omit<CreateOrderRequest, 'order_number'>): Observable<PurchaseOrder> {
    return this.http.patch<PurchaseOrder>(`${this.baseUrl}/purchase-orders/${encodeURIComponent(id)}`, request);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/purchase-orders/${encodeURIComponent(id)}`);
  }

  search(query: string, page = 1, filters?: OrderFilters): Observable<OrderPage> {
    let params = new HttpParams().set('search', query).set('page', page).set('page_size', 20);
    if (filters) {
      if (filters.branchId) params = params.set('branch_id', filters.branchId);
      if (filters.dateFrom) params = params.set('issue_date_from', filters.dateFrom);
      if (filters.dateTo) params = params.set('issue_date_to', filters.dateTo);
      params = params.set('sort_by', filters.sortBy).set('sort_order', filters.sortOrder);
    }
    return this.http.get<OrderPage>(`${this.baseUrl}/purchase-orders`, {
      params,
    });
  }
}

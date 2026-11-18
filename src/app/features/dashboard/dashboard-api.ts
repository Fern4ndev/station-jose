import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export interface DashboardFuel {
  readonly fuel_type_code: string;
  readonly fuel_type_name: string;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly attended_amount: string;
}

export interface DashboardPeriod {
  readonly period: string;
  readonly attended_gallons: string;
  readonly attended_amount: string;
  readonly attendances: number;
}

export interface DashboardResponse {
  readonly generated_at: string;
  readonly orders: number;
  readonly vouchers: number;
  readonly attendances: number;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly attended_amount: string;
  readonly by_fuel: readonly DashboardFuel[];
  readonly by_period: readonly DashboardPeriod[];
}

export interface DashboardQuery { readonly dateFrom: string; readonly dateTo: string; readonly branchId: string; readonly groupBy: 'hour' | 'day' | 'week' | 'month'; }

@Injectable({ providedIn: 'root' })
export class DashboardApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  getDashboard(query?: DashboardQuery): Observable<DashboardResponse> {
    let params = new HttpParams();
    if (query) {
      if (query.dateFrom) params = params.set('date_from', query.dateFrom);
      if (query.dateTo) params = params.set('date_to', query.dateTo);
      if (query.branchId) params = params.set('branch_id', query.branchId);
      params = params.set('group_by', query.groupBy);
    }
    return this.http.get<DashboardResponse>(`${this.baseUrl}/reports/dashboard`, { params });
  }
}

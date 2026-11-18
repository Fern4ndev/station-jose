import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';

export type ReportKind = 'purchase-orders' | 'attendances';
export interface ReportQuery { readonly dateFrom: string; readonly dateTo: string; readonly branchId: string; }
export interface ReportResponse { readonly items: readonly Readonly<Record<string, string | number | null>>[]; readonly total: number; readonly generated_at: string; }

@Injectable({ providedIn: 'root' })
export class ReportApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  get(kind: ReportKind, query: ReportQuery): Observable<ReportResponse> {
    return this.http.get<ReportResponse>(`${this.base}/reports/${kind}`, { params: this.params(query) });
  }

  export(kind: ReportKind, query: ReportQuery, format: 'pdf' | 'xlsx'): Observable<Blob> {
    return this.http.get(`${this.base}/reports/${kind}/export`, { params: this.params(query).set('format', format), responseType: 'blob' });
  }

  private params(query: ReportQuery): HttpParams {
    let params = new HttpParams();
    if (query.dateFrom) params = params.set('date_from', query.dateFrom);
    if (query.dateTo) params = params.set('date_to', query.dateTo);
    if (query.branchId) params = params.set('branch_id', query.branchId);
    return params;
  }
}

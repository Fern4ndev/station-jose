import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type {
  AttendanceReportQuery,
  AttendanceReportResponse,
  DashboardQuery,
  DashboardResponse,
  PurchaseOrderReportResponse,
  ReportExportFormat,
  ReportQuery,
} from '../models/report.model';
import { toHttpParams } from './http-params';

@Injectable({ providedIn: 'root' })
export class ReportsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  dashboard(query: DashboardQuery = {}): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(`${this.baseUrl}${API_ENDPOINTS.reports.dashboard}`, {
      params: toHttpParams(query),
    });
  }

  purchaseOrders(query: ReportQuery = {}): Observable<PurchaseOrderReportResponse> {
    return this.http.get<PurchaseOrderReportResponse>(
      `${this.baseUrl}${API_ENDPOINTS.reports.purchaseOrders}`,
      { params: toHttpParams(query) },
    );
  }

  attendances(query: AttendanceReportQuery = {}): Observable<AttendanceReportResponse> {
    return this.http.get<AttendanceReportResponse>(
      `${this.baseUrl}${API_ENDPOINTS.reports.attendances}`,
      { params: toHttpParams(query) },
    );
  }

  exportPurchaseOrders(
    format: ReportExportFormat,
    query: ReportQuery = {},
  ): Observable<Blob> {
    return this.http.get(`${this.baseUrl}${API_ENDPOINTS.reports.purchaseOrdersExport}`, {
      params: toHttpParams({ format, ...query }),
      responseType: 'blob',
    });
  }

  exportAttendances(
    format: ReportExportFormat,
    query: AttendanceReportQuery = {},
  ): Observable<Blob> {
    return this.http.get(`${this.baseUrl}${API_ENDPOINTS.reports.attendancesExport}`, {
      params: toHttpParams({ format, ...query }),
      responseType: 'blob',
    });
  }
}

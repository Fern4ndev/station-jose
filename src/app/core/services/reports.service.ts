import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi, apiUrl, toParams } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  AttendanceReportQuery,
  AttendanceReportResponse,
  DashboardQuery,
  DashboardResponse,
  PurchaseOrderReportResponse,
  ReportExportFormat,
  ReportQuery,
} from '../models/report.model';

/** Reportes: dashboard y listados analíticos, con caché reactiva por consulta. */
@Injectable({ providedIn: 'root' })
export class ReportsService extends BaseApi {
  private readonly loadingState = signal(false);
  private readonly dashboardState = signal<DashboardResponse | null>(null);
  private readonly ordersState = signal<PurchaseOrderReportResponse | null>(null);
  private readonly attendancesState = signal<AttendanceReportResponse | null>(null);

  readonly loading = this.loadingState.asReadonly();
  readonly dashboard = this.dashboardState.asReadonly();
  readonly orders = this.ordersState.asReadonly();
  readonly attendances = this.attendancesState.asReadonly();

  loadDashboard(query: DashboardQuery = {}): Observable<DashboardResponse> {
    this.loadingState.set(true);
    return this.get<DashboardResponse>(API_ENDPOINTS.reports.dashboard, query).pipe(
      tap((report) => this.dashboardState.set(report)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  loadPurchaseOrders(query: ReportQuery = {}): Observable<PurchaseOrderReportResponse> {
    this.loadingState.set(true);
    return this.get<PurchaseOrderReportResponse>(
      API_ENDPOINTS.reports.purchaseOrders,
      query,
    ).pipe(
      tap((report) => this.ordersState.set(report)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  loadAttendances(query: AttendanceReportQuery = {}): Observable<AttendanceReportResponse> {
    this.loadingState.set(true);
    return this.get<AttendanceReportResponse>(
      API_ENDPOINTS.reports.attendances,
      query,
    ).pipe(
      tap((report) => this.attendancesState.set(report)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  /** La exportación devuelve un binario, así que usa `HttpClient` directamente. */
  exportPurchaseOrders(
    format: ReportExportFormat,
    query: ReportQuery = {},
  ): Observable<Blob> {
    return this.http.get(apiUrl(API_ENDPOINTS.reports.purchaseOrdersExport), {
      params: toParams({ format, ...query }),
      responseType: 'blob',
    });
  }

  exportAttendances(
    format: ReportExportFormat,
    query: AttendanceReportQuery = {},
  ): Observable<Blob> {
    return this.http.get(apiUrl(API_ENDPOINTS.reports.attendancesExport), {
      params: toParams({ format, ...query }),
      responseType: 'blob',
    });
  }
}

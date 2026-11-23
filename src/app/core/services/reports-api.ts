import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';

/* Contratos exclusivos de este router: nadie más los consume. */

export type ReportGrouping = 'hour' | 'day' | 'week' | 'month';
export type ReportExportFormat = 'pdf' | 'xlsx';

export interface ReportFilters {
  readonly date_from?: string | null;
  readonly date_to?: string | null;
  readonly user_id?: string | null;
  readonly branch_id?: string | null;
  readonly status?: string | null;
  readonly group_by?: ReportGrouping;
}

export interface FuelDashboardRow {
  readonly fuel_type_code: string;
  readonly fuel_type_name: string;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly attended_amount: string;
}

export interface PeriodDashboardRow {
  readonly period: string;
  readonly attended_gallons: string;
  readonly attended_amount: string;
  readonly attendances: number;
}

export interface DashboardResponse {
  readonly generated_at: string;
  readonly filters: ReportFilters;
  readonly orders: number;
  readonly vouchers: number;
  readonly attendances: number;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly attended_amount: string;
  readonly by_fuel: readonly FuelDashboardRow[];
  readonly by_period: readonly PeriodDashboardRow[];
}

export interface PurchaseOrderReportRow {
  readonly order_id: string;
  readonly order_number: string;
  readonly institution_name: string;
  readonly branch_name: string;
  readonly issue_date: string;
  readonly fuel_type_code: string;
  readonly fuel_type_name: string;
  readonly authorized_gallons: string;
  readonly attended_gallons: string;
  readonly available_gallons: string;
  readonly status: string;
  readonly unit_price: string;
  readonly total_amount: string;
}

export interface PurchaseOrderReportResponse {
  readonly generated_at: string;
  readonly filters: ReportFilters;
  readonly items: readonly PurchaseOrderReportRow[];
  readonly total: number;
}

export interface AttendanceReportRow {
  readonly attendance_id: string;
  readonly voucher_id: string;
  readonly voucher_number: string;
  readonly order_id: string;
  readonly order_number: string;
  readonly attended_at: string;
  readonly performed_by_user_id: string;
  readonly performer_name: string;
  readonly branch_name: string;
  readonly fuel_type_code: string;
  readonly fuel_type_name: string;
  readonly attended_gallons: string;
  readonly unit_price: string;
  readonly attended_amount: string;
}

export interface AttendanceReportResponse {
  readonly generated_at: string;
  readonly filters: ReportFilters;
  readonly items: readonly AttendanceReportRow[];
  readonly total: number;
}

export type ReportQuery = {
  readonly date_from?: string | null;
  readonly date_to?: string | null;
  readonly branch_id?: string | null;
  readonly status?: string | null;
};

export type AttendanceReportQuery = {
  readonly date_from?: string | null;
  readonly date_to?: string | null;
  readonly user_id?: string | null;
  readonly branch_id?: string | null;
};

export type DashboardQuery = AttendanceReportQuery & {
  readonly status?: string | null;
  readonly group_by?: ReportGrouping;
};

/** Reportes y dashboard: consultas analíticas y exportaciones binarias. */
@Injectable({ providedIn: 'root' })
export class ReportsApi extends BaseApi {
  dashboard(query: DashboardQuery = {}): Observable<DashboardResponse> {
    return this.get<DashboardResponse>(API_ENDPOINTS.reports.dashboard, query);
  }

  purchaseOrders(query: ReportQuery = {}): Observable<PurchaseOrderReportResponse> {
    return this.get<PurchaseOrderReportResponse>(
      API_ENDPOINTS.reports.purchaseOrders,
      query,
    );
  }

  attendances(query: AttendanceReportQuery = {}): Observable<AttendanceReportResponse> {
    return this.get<AttendanceReportResponse>(API_ENDPOINTS.reports.attendances, query);
  }

  exportPurchaseOrders(
    format: ReportExportFormat,
    query: ReportQuery = {},
  ): Observable<Blob> {
    return this.getBlob(API_ENDPOINTS.reports.purchaseOrdersExport, {
      format,
      ...query,
    });
  }

  exportAttendances(
    format: ReportExportFormat,
    query: AttendanceReportQuery = {},
  ): Observable<Blob> {
    return this.getBlob(API_ENDPOINTS.reports.attendancesExport, {
      format,
      ...query,
    });
  }
}

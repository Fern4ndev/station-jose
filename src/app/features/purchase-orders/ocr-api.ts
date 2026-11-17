import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';
import { OcrPreviewResult } from './ocr-preview/ocr-preview';

interface OcrResponse {
  readonly fields: { readonly order_number: string | null; readonly siaf_number: string | null; readonly issue_date: string | null; readonly institution_name: string | null; readonly supplier_name: string | null; readonly executing_unit: string | null; readonly executing_unit_ruc: string | null; readonly lines: readonly { readonly fuel_description: string | null; readonly authorized_gallons: string | null; readonly unit_price: string | null; readonly total_amount: string | null }[] };
  readonly unrecognized_fields: readonly string[];
  readonly warnings: readonly string[];
}

@Injectable({ providedIn: 'root' })
export class OcrApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  preview(file: File): Observable<OcrPreviewResult> {
    const body = new FormData(); body.append('file', file);
    return this.http.post<OcrResponse>(`${this.base}/ocr/purchase-order-previews`, body).pipe(map((result) => ({
      fields: { orderNumber: result.fields.order_number, siafNumber: result.fields.siaf_number, issueDate: result.fields.issue_date, institutionName: result.fields.institution_name, supplierName: result.fields.supplier_name, executingUnit: result.fields.executing_unit, executingUnitRuc: result.fields.executing_unit_ruc,
        lines: result.fields.lines.map((line) => ({ fuelDescription: line.fuel_description, authorizedGallons: line.authorized_gallons, unitPrice: line.unit_price, totalAmount: line.total_amount })) },
      unrecognizedFields: result.unrecognized_fields, warnings: result.warnings, requiresManualReview: true,
    })));
  }
}

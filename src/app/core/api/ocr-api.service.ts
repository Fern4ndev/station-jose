import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type { PurchaseOrderOcrPreview } from '../models/ocr.model';

@Injectable({ providedIn: 'root' })
export class OcrApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  preview(file: File): Observable<PurchaseOrderOcrPreview> {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<PurchaseOrderOcrPreview>(
      `${this.baseUrl}${API_ENDPOINTS.ocr.purchaseOrderPreviews}`,
      body,
    );
  }
}

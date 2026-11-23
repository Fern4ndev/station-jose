import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type { PurchaseOrderOcrPreview } from '../models/ocr.model';

/** OCR de órdenes: sube una imagen y guarda la última vista previa leída. */
@Injectable({ providedIn: 'root' })
export class OcrService extends BaseApi {
  private readonly processingState = signal(false);
  private readonly previewState = signal<PurchaseOrderOcrPreview | null>(null);

  readonly processing = this.processingState.asReadonly();
  readonly preview = this.previewState.asReadonly();

  analyze(file: File): Observable<PurchaseOrderOcrPreview> {
    const body = new FormData();
    body.append('file', file);
    this.processingState.set(true);
    return this.post<PurchaseOrderOcrPreview>(
      API_ENDPOINTS.ocr.purchaseOrderPreviews,
      body,
    ).pipe(
      tap((preview) => this.previewState.set(preview)),
      finalize(() => this.processingState.set(false)),
    );
  }
}

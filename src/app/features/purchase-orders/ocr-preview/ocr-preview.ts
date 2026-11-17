import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface OcrLineCandidate {
  readonly fuelDescription: string | null;
  readonly authorizedGallons: string | null;
  readonly unitPrice: string | null;
  readonly totalAmount: string | null;
}

export interface OcrPurchaseOrderCandidates {
  readonly orderNumber: string | null;
  readonly siafNumber: string | null;
  readonly issueDate: string | null;
  readonly institutionName: string | null;
  readonly supplierName: string | null;
  readonly executingUnit: string | null;
  readonly executingUnitRuc: string | null;
  readonly lines: readonly OcrLineCandidate[];
}

export interface OcrPreviewResult {
  readonly fields: OcrPurchaseOrderCandidates;
  readonly unrecognizedFields: readonly string[];
  readonly warnings: readonly string[];
  readonly requiresManualReview: true;
}

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-ocr-preview', templateUrl: './ocr-preview.html' })
export class OcrPreview {
  readonly preview = input.required<OcrPreviewResult>();
  readonly applyCandidates = output<OcrPurchaseOrderCandidates>();
  readonly dismiss = output<void>();
}

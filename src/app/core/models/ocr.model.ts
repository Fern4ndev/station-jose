export interface OcrLineCandidate {
  readonly fuel_description?: string | null;
  readonly authorized_gallons?: string | null;
  readonly unit_price?: string | null;
  readonly total_amount?: string | null;
}

export interface PurchaseOrderOcrFields {
  readonly order_number?: string | null;
  readonly siaf_number?: string | null;
  readonly issue_date?: string | null;
  readonly institution_name?: string | null;
  readonly supplier_name?: string | null;
  readonly executing_unit?: string | null;
  readonly executing_unit_ruc?: string | null;
  readonly lines?: readonly OcrLineCandidate[];
}

export interface PurchaseOrderOcrPreview {
  readonly filename: string;
  readonly content_type: string;
  readonly pages_processed: number;
  readonly extracted_text: string;
  readonly fields: PurchaseOrderOcrFields;
  readonly unrecognized_fields: readonly string[];
  readonly warnings: readonly string[];
  readonly requires_manual_review?: boolean;
}

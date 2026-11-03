-- Migración 0011: conservar los datos detallados OCR revisados en la orden.
ALTER TABLE ordenes_compra
    ADD COLUMN IF NOT EXISTS datos_documento_ocr jsonb;

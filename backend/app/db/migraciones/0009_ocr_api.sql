-- Migración 0009: API de extracciones OCR (Fase 11).
-- La tabla existe desde 0001_base.sql; aquí se agrega la cadena de reintentos
-- y los índices/garantías que necesita la API e historial.

-- ---
ALTER TABLE ocr_extracciones
    ADD COLUMN IF NOT EXISTS reintento_de_id bigint
    REFERENCES ocr_extracciones(id) ON DELETE RESTRICT;

-- ---
ALTER TABLE ocr_extracciones ADD COLUMN IF NOT EXISTS archivo_hash text;

-- ---
ALTER TABLE ocr_extracciones ADD COLUMN IF NOT EXISTS archivo_tamano bigint;

-- ---
CREATE INDEX IF NOT EXISTS ix_ocr_reintento
    ON ocr_extracciones (reintento_de_id)
    WHERE reintento_de_id IS NOT NULL;

-- ---
CREATE INDEX IF NOT EXISTS ix_ocr_orden
    ON ocr_extracciones (orden_compra_id)
    WHERE orden_compra_id IS NOT NULL;

-- ---
DO $$ BEGIN
    ALTER TABLE ocr_extracciones
        ADD CONSTRAINT ocr_confirmada_con_orden
        CHECK (estado <> 'confirmada' OR orden_compra_id IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

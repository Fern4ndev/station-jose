-- Migración 0005: órdenes de compra (Fase 5, ORD-01..11).
-- Las tablas `instituciones` y `ordenes_compra` existen desde la línea base
-- `0001_base.sql` con sus índices, la unicidad `(institucion_id, anio, numero)`
-- y el CHECK del RUC de 11 dígitos; los GRANT de `0001` ya cubren ambas, así
-- que esta migración solo añade los metadatos del documento original que el
-- plan exige (ORD-03/04): ruta relativa (existente), tipo MIME real validado
-- por contenido, tamaño en bytes y hash SHA-256 del archivo.
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS archivo_tipo text;

-- ---
ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS archivo_tamano bigint;

-- ---
ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS archivo_hash text;

-- ---
-- Metadatos completos o ninguno: no queda un archivo con ruta pero sin hash.
ALTER TABLE ordenes_compra ADD CONSTRAINT ordenes_archivo_completo CHECK (
    (archivo_path IS NULL
        OR (archivo_tipo IS NOT NULL AND archivo_tamano IS NOT NULL AND archivo_hash IS NOT NULL))
);

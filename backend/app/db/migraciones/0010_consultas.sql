-- Índices de consulta: las tablas de vales y movimientos crecen con el uso.
-- Los índices por orden, entidad y fecha/tipo ya existen desde 0001; este
-- índice cubre el filtro conjunto de vale y fecha de negocio.

-- ---
CREATE INDEX IF NOT EXISTS ix_movimientos_vale_fecha_local
    ON movimientos_vale (vale_id, fecha_local);

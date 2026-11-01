-- Migración 0006: vales de combustible (Fase 6, VAL-01..15, QRY-01).
-- Las tablas `vales` y `movimientos_vale` ya existen desde la línea base
-- `0001_base.sql` con todas las columnas que el plan exige para esta fase
-- (numeración según emisor, `clave_numeracion`, `valor_comprometido_soles`,
-- `saldo >= 0`, `token_operacion` único para reenvíos, `movimiento_origen_id`
-- para reversiones) y los GRANT de `0001` ya limitan `movimientos_vale`
-- a SELECT e INSERT. Esta migración añade la integridad que la fase exige
-- y que la línea base no declaraba: el motivo obligatorio de ajustes y
-- anulaciones (VAL-10, VAL-11, RN-09).
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
ALTER TABLE movimientos_vale DROP CONSTRAINT IF EXISTS movimientos_motivo_obligatorio;

-- ---
-- Ajustes (VAL-11) y anulaciones (VAL-10) llevan motivo en el movimiento.
ALTER TABLE movimientos_vale ADD CONSTRAINT movimientos_motivo_obligatorio CHECK (
    tipo NOT IN ('ajuste', 'anulacion') OR nullif(trim(motivo), '') IS NOT NULL
);

-- ---
COMMENT ON TABLE vales IS
    'Vales de la estación y de entidad. La numeración es texto: sin código de barras ni QR (Fase 6).';

-- ---
COMMENT ON COLUMN movimientos_vale.variacion IS
    'Galones con signo: emision positivos, consumo/anulacion/ajuste con su signo real.';

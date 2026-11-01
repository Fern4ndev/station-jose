-- Migración 0007: disparadores de inalterabilidad (Fase 6, AUD-02, RN-11).
-- Los disparadores `BEFORE UPDATE OR DELETE` (por fila) sobre
-- `movimientos_vale` y `auditoria` ya existen en `0001_base.sql`; aquí se
-- completa el modelo del plan con la versión `BEFORE TRUNCATE` (por
-- sentencia), que impide el `TRUNCATE TABLE` incluso al rol dueño del
-- esquema. Las pruebas de limpieza los desactivan de forma explícita y
-- `vales_app` no puede desactivarlos ni truncar (GRANT limitado).
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
DROP TRIGGER IF EXISTS movimientos_vale_sin_truncate ON movimientos_vale;

-- ---
CREATE TRIGGER movimientos_vale_sin_truncate
BEFORE TRUNCATE ON movimientos_vale
FOR EACH STATEMENT EXECUTE FUNCTION rechazar_mutacion_inmutable();

-- ---
DROP TRIGGER IF EXISTS auditoria_sin_truncate ON auditoria;

-- ---
CREATE TRIGGER auditoria_sin_truncate
BEFORE TRUNCATE ON auditoria
FOR EACH STATEMENT EXECUTE FUNCTION rechazar_mutacion_inmutable();

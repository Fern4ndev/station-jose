-- Migración 0008: integridad de saldos (Fase 8, AUD-05/AUD-06).
-- Las tablas `verificaciones_integridad` y `diferencias_integridad` existen
-- desde `0001_base.sql`; aquí se agregan las garantías que asume el servicio:
-- una sola alerta pendiente por vale, los índices de consulta de la bitácora
-- y el disparador que impide reescribir o borrar una diferencia detectada.
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
-- Una única alerta pendiente por vale: la verificación refresca la alerta
-- abierta en vez de sembrar filas repetidas. Las diferencias revisadas quedan
-- fuera del índice parcial, de modo que una reincidencia sí crea fila nueva.
CREATE UNIQUE INDEX IF NOT EXISTS ux_diferencias_pendientes_vale
ON diferencias_integridad (vale_id) WHERE NOT revisada;

-- ---
CREATE INDEX IF NOT EXISTS ix_auditoria_accion_fecha ON auditoria (accion, creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_verificaciones_fecha ON verificaciones_integridad (creado_en DESC);

-- ---
-- La diferencia detectada es evidencia: mientras está pendiente solo se
-- refrescan los saldos comparados; al revisarse queda congelada (no se
-- reabre ni se corrige) y nunca se elimina.
CREATE OR REPLACE FUNCTION proteger_diferencia_integridad()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'La diferencia % es evidencia de auditoría y no se elimina', OLD.id
            USING ERRCODE = '55000';
    END IF;
    IF OLD.revisada THEN
        RAISE EXCEPTION 'La diferencia % ya fue revisada y no se modifica', OLD.id
            USING ERRCODE = '55000';
    END IF;
    IF NEW.id <> OLD.id
       OR NEW.vale_id <> OLD.vale_id
       OR NEW.creado_en IS DISTINCT FROM OLD.creado_en THEN
        RAISE EXCEPTION 'El origen de la diferencia % es inmutable', OLD.id
            USING ERRCODE = '55000';
    END IF;
    IF NEW.revisada AND NEW.revisada_en IS NULL THEN
        NEW.revisada_en := now();
    END IF;
    RETURN NEW;
END;
$$;

-- ---
DROP TRIGGER IF EXISTS diferencias_integridad_protegidas ON diferencias_integridad;

-- ---
CREATE TRIGGER diferencias_integridad_protegidas
BEFORE UPDATE OR DELETE ON diferencias_integridad
FOR EACH ROW EXECUTE FUNCTION proteger_diferencia_integridad();

-- Migración 0002: refresh_tokens.ultimo_uso_en
-- Los servicios de sesión (Fase 2) registran la actividad de la sesión en
-- cada petición autenticada para aplicar la expiración por inactividad
-- (AUT-08) con el parámetro `sesion_inactividad_min`.
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS ultimo_uso_en timestamptz;

-- ---
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_ultimo_uso ON refresh_tokens (app_user_id, ultimo_uso_en DESC);

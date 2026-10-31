-- Esquema inicial de San José.
-- PostgreSQL 16+. Requiere que exista el rol de runtime `vales_app` antes de
-- ejecutar el GRANT al final. Aplicar como propietario/migrador del esquema:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/db/schema.sql
-- Idempotencia: usa IF NOT EXISTS para permitir re-ejecuciones de desarrollo.

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version         text PRIMARY KEY,
    nombre          text NOT NULL,
    checksum        text NOT NULL,
    aplicado_en    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS estaciones (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              text NOT NULL,
    ruc                 varchar(11),
    direccion           text,
    telefono            text,
    correo              text,
    logo_path           text,
    activo              boolean NOT NULL DEFAULT true,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT estaciones_ruc_formato CHECK (ruc IS NULL OR ruc ~ '^[0-9]{11}$')
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_estaciones_nombre_lower ON estaciones (lower(nombre));

CREATE TABLE IF NOT EXISTS usuarios (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre                  text NOT NULL,
    correo                  text NOT NULL,
    password_hash           text NOT NULL,
    rol                     text NOT NULL,
    estacion_id             bigint REFERENCES estaciones(id) ON DELETE RESTRICT,
    activo                  boolean NOT NULL DEFAULT true,
    debe_cambiar_password   boolean NOT NULL DEFAULT true,
    password_cambiado_en    timestamptz,
    ultimo_acceso_en        timestamptz,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    actualizado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT usuarios_rol_valido CHECK (rol IN ('administrador', 'oficina', 'despachador')),
    CONSTRAINT usuarios_correo_no_vacio CHECK (length(trim(correo)) > 3)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_correo_lower ON usuarios (lower(correo));
CREATE INDEX IF NOT EXISTS ix_usuarios_rol_activo ON usuarios (rol, activo);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id          bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    familia_id          uuid NOT NULL,
    token_hash          varchar(64) NOT NULL,
    emitido_en          timestamptz NOT NULL DEFAULT now(),
    expira_en           timestamptz NOT NULL,
    revocado_en         timestamptz,
    reemplazado_por_id  bigint REFERENCES refresh_tokens(id) ON DELETE RESTRICT,
    ip                  inet,
    user_agent          text,
    CONSTRAINT refresh_tokens_hash_hex CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT refresh_tokens_expira_despues CHECK (expira_en > emitido_en)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_refresh_tokens_hash ON refresh_tokens (token_hash);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_usuario ON refresh_tokens (usuario_id, expira_en DESC);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_familia ON refresh_tokens (familia_id);

CREATE TABLE IF NOT EXISTS intentos_login (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correo          text NOT NULL,
    ip              inet,
    exitoso         boolean NOT NULL DEFAULT false,
    motivo          text,
    creado_en       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_intentos_login_correo_fecha ON intentos_login (lower(correo), creado_en DESC);
CREATE INDEX IF NOT EXISTS ix_intentos_login_ip_fecha ON intentos_login (ip, creado_en DESC);

CREATE TABLE IF NOT EXISTS tokens_recuperacion (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id      bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    token_hash      varchar(64) NOT NULL,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    expira_en       timestamptz NOT NULL,
    usado_en        timestamptz,
    CONSTRAINT tokens_recuperacion_hash_hex CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT tokens_recuperacion_expira_despues CHECK (expira_en > creado_en)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tokens_recuperacion_hash ON tokens_recuperacion (token_hash);
CREATE INDEX IF NOT EXISTS ix_tokens_recuperacion_usuario ON tokens_recuperacion (usuario_id, expira_en DESC);

CREATE TABLE IF NOT EXISTS parametros (
    clave           text PRIMARY KEY,
    valor           text NOT NULL,
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_por bigint REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS combustibles (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre          text NOT NULL,
    activo          boolean NOT NULL DEFAULT true,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT combustibles_nombre_no_vacio CHECK (length(trim(nombre)) > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_combustibles_nombre_lower ON combustibles (lower(nombre));

CREATE TABLE IF NOT EXISTS precios_combustible (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    combustible_id  bigint NOT NULL REFERENCES combustibles(id) ON DELETE RESTRICT,
    precio_galon    numeric(12,2) NOT NULL CHECK (precio_galon > 0),
    vigente_desde   date NOT NULL,
    usuario_id      bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT precios_combustible_fecha_unica UNIQUE (combustible_id, vigente_desde)
);
CREATE INDEX IF NOT EXISTS ix_precios_combustible_vigencia ON precios_combustible (combustible_id, vigente_desde DESC);

CREATE TABLE IF NOT EXISTS instituciones (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              text NOT NULL,
    ruc                 varchar(11) NOT NULL,
    tipo                text NOT NULL,
    telefono            text,
    correo              text,
    direccion           text,
    representante       text,
    modalidad_numeracion text NOT NULL DEFAULT 'no_aplica',
    estado              text NOT NULL DEFAULT 'activa',
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT instituciones_ruc_formato CHECK (ruc ~ '^[0-9]{11}$'),
    CONSTRAINT instituciones_tipo_valido CHECK (tipo IN ('publica', 'privada', 'ong', 'otra')),
    CONSTRAINT instituciones_numeracion_valida CHECK (modalidad_numeracion IN ('general', 'por_orden', 'no_aplica')),
    CONSTRAINT instituciones_estado_valido CHECK (estado IN ('activa', 'inactiva'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_instituciones_ruc ON instituciones (ruc);
CREATE INDEX IF NOT EXISTS ix_instituciones_nombre_lower ON instituciones (lower(nombre));

CREATE TABLE IF NOT EXISTS ordenes_compra (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    institucion_id      bigint NOT NULL REFERENCES instituciones(id) ON DELETE RESTRICT,
    numero              text NOT NULL,
    anio                smallint NOT NULL,
    fecha_emision       date NOT NULL,
    presupuesto_soles   numeric(14,2) NOT NULL CHECK (presupuesto_soles > 0),
    combustible_id      bigint REFERENCES combustibles(id) ON DELETE RESTRICT,
    estado              text NOT NULL DEFAULT 'borrador',
    serie_desde         integer,
    serie_hasta         integer,
    creada_con_ocr      boolean NOT NULL DEFAULT false,
    archivo_path        text,
    observaciones       text,
    motivo_anulacion    text,
    creado_por          bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ordenes_numero_unico_por_institucion_anio UNIQUE (institucion_id, anio, numero),
    CONSTRAINT ordenes_estado_valido CHECK (estado IN ('borrador', 'vigente', 'cerrada', 'anulada')),
    CONSTRAINT ordenes_anio_valido CHECK (anio BETWEEN 2000 AND 2200),
    CONSTRAINT ordenes_serie_valida CHECK (
        (serie_desde IS NULL AND serie_hasta IS NULL)
        OR (serie_desde IS NOT NULL AND serie_hasta IS NOT NULL AND serie_desde > 0 AND serie_hasta >= serie_desde)
    ),
    CONSTRAINT ordenes_anulacion_con_motivo CHECK (estado <> 'anulada' OR nullif(trim(motivo_anulacion), '') IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS ix_ordenes_institucion_fecha ON ordenes_compra (institucion_id, fecha_emision DESC);
CREATE INDEX IF NOT EXISTS ix_ordenes_estado_fecha ON ordenes_compra (estado, fecha_emision DESC);

CREATE TABLE IF NOT EXISTS ocr_extracciones (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id          bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    archivo_path        text NOT NULL,
    archivo_nombre      text NOT NULL,
    archivo_mime        text NOT NULL,
    estado              text NOT NULL DEFAULT 'pendiente',
    metodo              text,
    resultado           jsonb NOT NULL DEFAULT '{}'::jsonb,
    campos_finales      jsonb NOT NULL DEFAULT '{}'::jsonb,
    correcciones        jsonb NOT NULL DEFAULT '{}'::jsonb,
    confianza_promedio  numeric(5,4),
    tiempo_ms           integer,
    version_pipeline    text,
    error_codigo        text,
    error_detalle       text,
    orden_compra_id     bigint REFERENCES ordenes_compra(id) ON DELETE RESTRICT,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ocr_estado_valido CHECK (estado IN ('pendiente', 'procesando', 'lista', 'fallida', 'confirmada', 'descartada')),
    CONSTRAINT ocr_metodo_valido CHECK (metodo IS NULL OR metodo IN ('texto_digital', 'ocr')),
    CONSTRAINT ocr_confianza_valida CHECK (confianza_promedio IS NULL OR confianza_promedio BETWEEN 0 AND 1),
    CONSTRAINT ocr_tiempo_valido CHECK (tiempo_ms IS NULL OR tiempo_ms >= 0)
);
CREATE INDEX IF NOT EXISTS ix_ocr_usuario_fecha ON ocr_extracciones (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS ix_ocr_estado_fecha ON ocr_extracciones (estado, creado_en DESC);

CREATE TABLE IF NOT EXISTS secuencias (
    nombre      text NOT NULL,
    anio        smallint NOT NULL,
    ultimo      bigint NOT NULL DEFAULT 0 CHECK (ultimo >= 0),
    PRIMARY KEY (nombre, anio)
);

CREATE TABLE IF NOT EXISTS vales (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_interno          text NOT NULL,
    numero_entidad          text,
    clave_numeracion        text,
    orden_compra_id         bigint NOT NULL REFERENCES ordenes_compra(id) ON DELETE RESTRICT,
    emisor                  text NOT NULL,
    combustible_id          bigint NOT NULL REFERENCES combustibles(id) ON DELETE RESTRICT,
    cantidad_inicial        numeric(12,2) NOT NULL CHECK (cantidad_inicial > 0),
    precio_galon_aplicado   numeric(12,2) NOT NULL CHECK (precio_galon_aplicado > 0),
    valor_soles             numeric(14,2) NOT NULL CHECK (valor_soles > 0),
    valor_comprometido_soles numeric(14,2) NOT NULL CHECK (valor_comprometido_soles >= 0),
    saldo                   numeric(12,2) NOT NULL CHECK (saldo >= 0 AND saldo <= cantidad_inicial),
    estado                  text NOT NULL DEFAULT 'activo',
    fecha_emision           date NOT NULL DEFAULT ((now() AT TIME ZONE 'America/Lima')::date),
    fecha_vencimiento       date,
    veces_impreso           integer NOT NULL DEFAULT 0 CHECK (veces_impreso >= 0),
    creado_por              bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    actualizado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT vales_codigo_interno_unico UNIQUE (codigo_interno),
    CONSTRAINT vales_emisor_valido CHECK (emisor IN ('estacion', 'entidad')),
    CONSTRAINT vales_estado_valido CHECK (estado IN ('activo', 'agotado', 'vencido', 'anulado')),
    CONSTRAINT vales_vencimiento_valido CHECK (fecha_vencimiento IS NULL OR fecha_vencimiento >= fecha_emision),
    CONSTRAINT vales_saldo_estado CHECK ((saldo = 0 AND estado IN ('agotado', 'anulado')) OR (saldo > 0 AND estado IN ('activo', 'vencido'))),
    CONSTRAINT vales_numero_entidad_requerido CHECK (emisor <> 'entidad' OR nullif(trim(numero_entidad), '') IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_vales_clave_numeracion ON vales (clave_numeracion) WHERE clave_numeracion IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_vales_orden ON vales (orden_compra_id);
CREATE INDEX IF NOT EXISTS ix_vales_combustible_estado ON vales (combustible_id, estado);
CREATE INDEX IF NOT EXISTS ix_vales_vencimiento ON vales (fecha_vencimiento) WHERE estado = 'activo';
CREATE INDEX IF NOT EXISTS ix_vales_numero_entidad ON vales (numero_entidad) WHERE numero_entidad IS NOT NULL;

CREATE TABLE IF NOT EXISTS movimientos_vale (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vale_id             bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    tipo                text NOT NULL,
    variacion           numeric(12,2) NOT NULL,
    saldo_posterior     numeric(12,2) NOT NULL CHECK (saldo_posterior >= 0),
    cantidad_galones    numeric(12,2),
    precio_galon        numeric(12,2),
    importe_soles       numeric(14,2),
    usuario_id          bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    estacion_id         bigint NOT NULL REFERENCES estaciones(id) ON DELETE RESTRICT,
    motivo              text,
    placa               text,
    conductor           text,
    token_operacion     uuid,
    movimiento_origen_id bigint REFERENCES movimientos_vale(id) ON DELETE RESTRICT,
    fecha_local         date NOT NULL DEFAULT (now() AT TIME ZONE 'America/Lima')::date,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT movimientos_tipo_valido CHECK (tipo IN ('emision', 'consumo', 'anulacion', 'ajuste', 'reversion')),
    CONSTRAINT movimientos_consumo_datos CHECK (
        tipo <> 'consumo' OR (cantidad_galones > 0 AND precio_galon > 0 AND importe_soles > 0)
    ),
    CONSTRAINT movimientos_variacion_tipo CHECK (
        (tipo = 'emision' AND variacion > 0)
        OR (tipo = 'consumo' AND variacion < 0)
        OR (tipo = 'anulacion' AND variacion < 0)
        OR (tipo IN ('ajuste', 'reversion'))
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_movimientos_token_operacion ON movimientos_vale (token_operacion) WHERE token_operacion IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_movimientos_reversion_origen ON movimientos_vale (movimiento_origen_id) WHERE tipo = 'reversion' AND movimiento_origen_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_movimientos_vale_fecha ON movimientos_vale (vale_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS ix_movimientos_fecha_tipo ON movimientos_vale (fecha_local, tipo);
CREATE INDEX IF NOT EXISTS ix_movimientos_estacion_fecha ON movimientos_vale (estacion_id, creado_en DESC);

CREATE TABLE IF NOT EXISTS auditoria (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id      bigint REFERENCES usuarios(id) ON DELETE RESTRICT,
    accion          text NOT NULL,
    entidad         text NOT NULL,
    entidad_id      text,
    antes           jsonb,
    despues         jsonb,
    ip              inet,
    user_agent      text,
    creado_en       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_auditoria_usuario_fecha ON auditoria (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad_fecha ON auditoria (entidad, entidad_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS ix_auditoria_fecha ON auditoria (creado_en DESC);

CREATE TABLE IF NOT EXISTS verificaciones_integridad (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ejecutada_por       bigint REFERENCES usuarios(id) ON DELETE RESTRICT,
    vales_revisados     integer NOT NULL DEFAULT 0 CHECK (vales_revisados >= 0),
    diferencias        integer NOT NULL DEFAULT 0 CHECK (diferencias >= 0),
    creado_en           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS diferencias_integridad (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verificacion_id     bigint NOT NULL REFERENCES verificaciones_integridad(id) ON DELETE RESTRICT,
    vale_id             bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    saldo_almacenado    numeric(12,2) NOT NULL,
    saldo_recalculado   numeric(12,2) NOT NULL,
    revisada            boolean NOT NULL DEFAULT false,
    revisada_por        bigint REFERENCES usuarios(id) ON DELETE RESTRICT,
    revisada_en         timestamptz,
    comentario          text,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT diferencias_revisada_comentario CHECK (NOT revisada OR nullif(trim(comentario), '') IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS ix_diferencias_pendientes ON diferencias_integridad (revisada, creado_en DESC) WHERE NOT revisada;
CREATE INDEX IF NOT EXISTS ix_diferencias_vale ON diferencias_integridad (vale_id, creado_en DESC);

CREATE TABLE IF NOT EXISTS impresiones_vale (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vale_id         bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    usuario_id      bigint NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    es_duplicado    boolean NOT NULL DEFAULT false,
    creado_en       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_impresiones_vale_fecha ON impresiones_vale (vale_id, creado_en DESC);

CREATE OR REPLACE FUNCTION rechazar_mutacion_inmutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'La tabla %.% es inmutable', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS movimientos_vale_inmutables ON movimientos_vale;
CREATE TRIGGER movimientos_vale_inmutables
BEFORE UPDATE OR DELETE ON movimientos_vale
FOR EACH ROW EXECUTE FUNCTION rechazar_mutacion_inmutable();

DROP TRIGGER IF EXISTS auditoria_inmutable ON auditoria;
CREATE TRIGGER auditoria_inmutable
BEFORE UPDATE OR DELETE ON auditoria
FOR EACH ROW EXECUTE FUNCTION rechazar_mutacion_inmutable();

CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE tabla text;
BEGIN
    FOREACH tabla IN ARRAY ARRAY['estaciones', 'usuarios', 'combustibles', 'instituciones', 'ordenes_compra', 'ocr_extracciones', 'vales'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I_actualizado_en ON %I', tabla, tabla);
        EXECUTE format('CREATE TRIGGER %I_actualizado_en BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp()', tabla, tabla);
    END LOOP;
END;
$$;

-- Permisos mínimos para el rol de ejecución creado por el despliegue.
-- El usuario propietario/migrador conserva el control del esquema y DDL.
GRANT USAGE ON SCHEMA public TO vales_app;
GRANT SELECT, INSERT, UPDATE ON
    estaciones, usuarios, refresh_tokens, intentos_login, tokens_recuperacion,
    parametros, combustibles, precios_combustible, instituciones,
    ordenes_compra, ocr_extracciones, secuencias, vales,
    verificaciones_integridad, diferencias_integridad, impresiones_vale
TO vales_app;
GRANT SELECT, INSERT ON movimientos_vale, auditoria TO vales_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vales_app;

COMMIT;

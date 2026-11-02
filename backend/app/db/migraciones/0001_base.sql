-- Migración 0001: base
-- Esquema inicial del sistema: enums del dominio, tablas, integridad,
-- disparadores y permisos mínimos para `vales_app`. Es la versión numerada
-- de `backend/db/schema.sql` (bootstrap previo al ejecutor de migraciones).
--
-- La tabla de control `schema_migrations` NO vive aquí: la crea y mantiene
-- el ejecutor (`app.db.migrar`).
--
-- Idempotente respecto de instalaciones pobladas antes con `schema.sql`:
-- el ejecutor registra esta migración como aplicada sin volver a ejecutarla.
--
-- Complete aquí los parámetros por defecto del plan y el catálogo `secuencias`.

-- enums del dominio --- tipos cerrados; lo configurable vive en tablas
DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('administrador', 'oficina', 'despachador');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE institution_type AS ENUM ('publica', 'privada', 'ong', 'otra');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE institution_numbering AS ENUM ('general', 'por_orden', 'no_aplica');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE institution_status AS ENUM ('activa', 'inactiva');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE purchase_order_status AS ENUM ('borrador', 'vigente', 'cerrada', 'anulada');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE ocr_status AS ENUM ('pendiente', 'procesando', 'lista', 'fallida', 'confirmada', 'descartada');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE ocr_method AS ENUM ('texto_digital', 'ocr');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE voucher_issuer AS ENUM ('estacion', 'entidad');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE voucher_status AS ENUM ('activo', 'agotado', 'vencido', 'anulado');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
DO $$
BEGIN
    CREATE TYPE voucher_movement_type AS ENUM ('emision', 'consumo', 'anulacion', 'ajuste', 'reversion');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---
-- estaciones: sedes físicas de la estación de servicio, todas sobre la misma base
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

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_estaciones_nombre_lower ON estaciones (lower(nombre));

-- ---
-- app_users: cuentas de acceso. Sin columna `active` (no hay flujo de
-- activación). `must_change_password` es NULLable: solo TRUE obliga al cambio.
CREATE TABLE IF NOT EXISTS app_users (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name               text NOT NULL,
    email                   text NOT NULL,
    dni                     varchar(8),
    code                    text,
    password_hash           text NOT NULL,
    role                    user_role NOT NULL,
    station_id              bigint REFERENCES estaciones(id) ON DELETE RESTRICT,
    must_change_password    boolean,
    password_cambiado_en    timestamptz,
    ultimo_acceso_en        timestamptz,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    actualizado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT app_users_nombre_no_vacio CHECK (length(trim(full_name)) > 0),
    CONSTRAINT app_users_email_no_vacio CHECK (length(trim(email)) > 3),
    CONSTRAINT app_users_password_argon2id CHECK (password_hash LIKE '$argon2id$%'),
    CONSTRAINT app_users_dni_valido CHECK (dni IS NULL OR dni ~ '^[0-9]{8}$')
);

-- ---
-- Instalaciones de desarrollo creadas con el bootstrap anterior del esqueleto.
ALTER TABLE app_users DROP COLUMN IF EXISTS active;

-- ---
ALTER TABLE app_users ALTER COLUMN must_change_password DROP NOT NULL;

-- ---
ALTER TABLE app_users ALTER COLUMN must_change_password DROP DEFAULT;

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_app_users_email_lower ON app_users (lower(email));

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_app_users_dni ON app_users (dni) WHERE dni IS NOT NULL;

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_app_users_code ON app_users (code) WHERE code IS NOT NULL;

-- ---
CREATE INDEX IF NOT EXISTS ix_app_users_role ON app_users (role);

-- ---
-- refresh_tokens: opacos, aleatorios, rotatorios, guardados como hash.
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_user_id         bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
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

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_refresh_tokens_hash ON refresh_tokens (token_hash);

-- ---
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_usuario ON refresh_tokens (app_user_id, expira_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_familia ON refresh_tokens (familia_id);

-- ---
-- intentos_login: límite de intentos en PostgreSQL (sin Redis).
CREATE TABLE IF NOT EXISTS intentos_login (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    correo          text NOT NULL,
    ip              inet,
    exitoso         boolean NOT NULL DEFAULT false,
    motivo          text,
    creado_en       timestamptz NOT NULL DEFAULT now()
);

-- ---
CREATE INDEX IF NOT EXISTS ix_intentos_login_correo_fecha ON intentos_login (lower(correo), creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_intentos_login_ip_fecha ON intentos_login (ip, creado_en DESC);

-- ---
CREATE TABLE IF NOT EXISTS tokens_recuperacion (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_user_id     bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    token_hash      varchar(64) NOT NULL,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    expira_en       timestamptz NOT NULL,
    usado_en        timestamptz,
    CONSTRAINT tokens_recuperacion_hash_hex CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT tokens_recuperacion_expira_despues CHECK (expira_en > creado_en)
);

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_tokens_recuperacion_hash ON tokens_recuperacion (token_hash);

-- ---
CREATE INDEX IF NOT EXISTS ix_tokens_recuperacion_usuario ON tokens_recuperacion (app_user_id, expira_en DESC);

-- ---
-- parametros: configuración editable en caliente (CFG-01); códigos del plan.
CREATE TABLE IF NOT EXISTS parametros (
    clave           text PRIMARY KEY,
    valor           text NOT NULL,
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_por bigint REFERENCES app_users(id) ON DELETE RESTRICT
);

-- ---
INSERT INTO parametros (clave, valor)
VALUES
    ('ocr_umbral_confianza', '0.80'),
    ('archivo_max_mb', '10'),
    ('vale_formato_numeracion_estacion', '{anio}-{secuencia:06d}'),
    ('vale_vigencia_dias', ''),
    ('vale_umbral_saldo_bajo_pct', '10'),
    ('vale_dias_aviso_vencimiento', '7'),
    ('sesion_inactividad_min', '60'),
    ('login_intentos_max', '5'),
    ('login_bloqueo_min', '15'),
    ('refresh_token_dias', '30')
ON CONFLICT (clave) DO NOTHING;

-- ---
-- combustibles y sus precios (histórico inmutable de precios)
CREATE TABLE IF NOT EXISTS combustibles (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre          text NOT NULL,
    activo          boolean NOT NULL DEFAULT true,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT combustibles_nombre_no_vacio CHECK (length(trim(nombre)) > 0)
);

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_combustibles_nombre_lower ON combustibles (lower(nombre));

-- ---
CREATE TABLE IF NOT EXISTS precios_combustible (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    combustible_id  bigint NOT NULL REFERENCES combustibles(id) ON DELETE RESTRICT,
    precio_galon    numeric(12,2) NOT NULL CHECK (precio_galon > 0),
    vigente_desde   date NOT NULL,
    app_user_id     bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT precios_combustible_fecha_unica UNIQUE (combustible_id, vigente_desde)
);

-- ---
CREATE INDEX IF NOT EXISTS ix_precios_combustible_vigencia ON precios_combustible (combustible_id, vigente_desde DESC);

-- ---
-- instituciones, clientes de las órdenes de compra.
CREATE TABLE IF NOT EXISTS instituciones (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre              text NOT NULL,
    ruc                 varchar(11) NOT NULL,
    tipo                institution_type NOT NULL,
    telefono            text,
    correo              text,
    direccion           text,
    representante       text,
    modalidad_numeracion institution_numbering NOT NULL DEFAULT 'no_aplica',
    estado              institution_status NOT NULL DEFAULT 'activa',
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT instituciones_ruc_formato CHECK (ruc ~ '^[0-9]{11}$'),
    CONSTRAINT instituciones_nombre_no_vacio CHECK (length(trim(nombre)) > 0)
);

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_instituciones_ruc ON instituciones (ruc);

-- ---
CREATE INDEX IF NOT EXISTS ix_instituciones_nombre_lower ON instituciones (lower(nombre));

-- ---
-- ordenes_compra: presupuesto por institución, con serie opcional para los
-- vales de entidad con numeración por orden (decisiones D-01 y D-02).
CREATE TABLE IF NOT EXISTS ordenes_compra (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    institucion_id      bigint NOT NULL REFERENCES instituciones(id) ON DELETE RESTRICT,
    numero              text NOT NULL,
    anio                smallint NOT NULL,
    fecha_emision       date NOT NULL,
    presupuesto_soles   numeric(14,2) NOT NULL CHECK (presupuesto_soles > 0),
    combustible_id      bigint REFERENCES combustibles(id) ON DELETE RESTRICT,
    estado              purchase_order_status NOT NULL DEFAULT 'borrador',
    serie_desde         integer,
    serie_hasta         integer,
    creada_con_ocr      boolean NOT NULL DEFAULT false,
    archivo_path        text,
    observaciones       text,
    motivo_anulacion    text,
    creado_por          bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
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

-- ---
CREATE INDEX IF NOT EXISTS ix_ordenes_institucion_fecha ON ordenes_compra (institucion_id, fecha_emision DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_ordenes_estado_fecha ON ordenes_compra (estado, fecha_emision DESC);

-- ---
-- ocr_extracciones: registros del pipeline de OCR.
CREATE TABLE IF NOT EXISTS ocr_extracciones (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_user_id         bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    archivo_path        text NOT NULL,
    archivo_nombre      text NOT NULL,
    archivo_mime        text NOT NULL,
    estado              ocr_status NOT NULL DEFAULT 'pendiente',
    metodo              ocr_method,
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

-- ---
CREATE INDEX IF NOT EXISTS ix_ocr_usuario_fecha ON ocr_extracciones (app_user_id, creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_ocr_estado_fecha ON ocr_extracciones (estado, creado_en DESC);

-- ---
-- secuencias: contadores de numeración de vales por nombre y año.
CREATE TABLE IF NOT EXISTS secuencias (
    nombre      text NOT NULL,
    anio        smallint NOT NULL,
    ultimo      bigint NOT NULL DEFAULT 0 CHECK (ultimo >= 0),
    PRIMARY KEY (nombre, anio)
);

-- ---
-- vales: numeración sola, sin código de barras ni QR. `numero_estacion` es la
-- numeración propia de San José; `numero_entidad` la asigna la institución.
-- `clave_numeracion` da unicidad general por institución o reinicio por orden.
CREATE TABLE IF NOT EXISTS vales (
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero_estacion         text,
    numero_entidad          text,
    clave_numeracion        text,
    orden_compra_id         bigint NOT NULL REFERENCES ordenes_compra(id) ON DELETE RESTRICT,
    emisor                  voucher_issuer NOT NULL,
    combustible_id          bigint NOT NULL REFERENCES combustibles(id) ON DELETE RESTRICT,
    cantidad_inicial        numeric(12,2) NOT NULL CHECK (cantidad_inicial > 0),
    precio_galon_aplicado   numeric(12,2) NOT NULL CHECK (precio_galon_aplicado > 0),
    valor_soles             numeric(14,2) NOT NULL CHECK (valor_soles > 0),
    valor_comprometido_soles numeric(14,2) NOT NULL CHECK (valor_comprometido_soles >= 0),
    saldo                   numeric(12,2) NOT NULL CHECK (saldo >= 0 AND saldo <= cantidad_inicial),
    estado                  voucher_status NOT NULL DEFAULT 'activo',
    fecha_emision           date NOT NULL DEFAULT ((now() AT TIME ZONE 'America/Lima')::date),
    fecha_vencimiento       date,
    veces_impreso           integer NOT NULL DEFAULT 0 CHECK (veces_impreso >= 0),
    creado_por              bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    actualizado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT vales_numero_estacion_no_vacio CHECK (numero_estacion IS NULL OR length(trim(numero_estacion)) > 0),
    CONSTRAINT vales_numero_entidad_no_vacio CHECK (numero_entidad IS NULL OR length(trim(numero_entidad)) > 0),
    CONSTRAINT vales_vencimiento_valido CHECK (fecha_vencimiento IS NULL OR fecha_vencimiento >= fecha_emision),
    CONSTRAINT vales_saldo_estado CHECK ((saldo = 0 AND estado IN ('agotado', 'anulado')) OR (saldo > 0 AND estado IN ('activo', 'vencido'))),
    CONSTRAINT vales_numeracion_segun_emisor CHECK (
        (emisor = 'estacion' AND numero_estacion IS NOT NULL AND numero_entidad IS NULL AND clave_numeracion IS NULL)
        OR (emisor = 'entidad' AND numero_estacion IS NULL AND numero_entidad IS NOT NULL AND clave_numeracion IS NOT NULL)
    )
);
-- numero_estacion: numeración propia de la estación.
-- clave_numeracion para entidad: "institucion:<id>:<numero>" si es general,
-- o "orden:<id>:<numero>" si reinicia en cada orden de compra.

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_vales_numero_estacion ON vales (numero_estacion) WHERE numero_estacion IS NOT NULL;

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_vales_clave_numeracion ON vales (clave_numeracion) WHERE clave_numeracion IS NOT NULL;

-- ---
CREATE INDEX IF NOT EXISTS ix_vales_orden ON vales (orden_compra_id);

-- ---
CREATE INDEX IF NOT EXISTS ix_vales_combustible_estado ON vales (combustible_id, estado);

-- ---
CREATE INDEX IF NOT EXISTS ix_vales_vencimiento ON vales (fecha_vencimiento) WHERE estado = 'activo';

-- ---
CREATE INDEX IF NOT EXISTS ix_vales_numero_entidad ON vales (numero_entidad) WHERE numero_entidad IS NOT NULL;

-- ---
-- movimientos_vale: saldo derivado de variaciones con signo (RN-05, RN-08).
-- Inmutable: el rol de la aplicación solo tiene SELECT e INSERT; los
-- disparadores que siguen rechazan mutations para quien tenga UPDATE/DELETE.
CREATE TABLE IF NOT EXISTS movimientos_vale (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vale_id             bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    tipo                voucher_movement_type NOT NULL,
    variacion           numeric(12,2) NOT NULL,
    saldo_posterior     numeric(12,2) NOT NULL CHECK (saldo_posterior >= 0),
    cantidad_galones    numeric(12,2),
    precio_galon        numeric(12,2),
    importe_soles       numeric(14,2),
    app_user_id         bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    estacion_id         bigint NOT NULL REFERENCES estaciones(id) ON DELETE RESTRICT,
    motivo              text,
    placa               text,
    conductor           text,
    token_operacion     uuid,
    movimiento_origen_id bigint REFERENCES movimientos_vale(id) ON DELETE RESTRICT,
    fecha_local         date NOT NULL DEFAULT (now() AT TIME ZONE 'America/Lima')::date,
    creado_en           timestamptz NOT NULL DEFAULT now(),
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

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_movimientos_token_operacion ON movimientos_vale (token_operacion) WHERE token_operacion IS NOT NULL;

-- ---
CREATE UNIQUE INDEX IF NOT EXISTS ux_movimientos_reversion_origen ON movimientos_vale (movimiento_origen_id) WHERE tipo = 'reversion' AND movimiento_origen_id IS NOT NULL;

-- ---
CREATE INDEX IF NOT EXISTS ix_movimientos_vale_fecha ON movimientos_vale (vale_id, creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_movimientos_fecha_tipo ON movimientos_vale (fecha_local, tipo);

-- ---
CREATE INDEX IF NOT EXISTS ix_movimientos_estacion_fecha ON movimientos_vale (estacion_id, creado_en DESC);

-- ---
-- auditoria: bitácora inmutable de acciones (AUD-01, AUD-02).
CREATE TABLE IF NOT EXISTS auditoria (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_user_id     bigint REFERENCES app_users(id) ON DELETE RESTRICT,
    accion          text NOT NULL,
    entidad         text NOT NULL,
    entidad_id      text,
    antes           jsonb,
    despues         jsonb,
    ip              inet,
    user_agent      text,
    creado_en       timestamptz NOT NULL DEFAULT now()
);

-- ---
CREATE INDEX IF NOT EXISTS ix_auditoria_usuario_fecha ON auditoria (app_user_id, creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad_fecha ON auditoria (entidad, entidad_id, creado_en DESC);

-- ---
CREATE INDEX IF NOT EXISTS ix_auditoria_fecha ON auditoria (creado_en DESC);

-- ---
-- verificaciones_integridad y diferencias con el saldo recalculado.
CREATE TABLE IF NOT EXISTS verificaciones_integridad (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ejecutada_por       bigint REFERENCES app_users(id) ON DELETE RESTRICT,
    vales_revisados     integer NOT NULL DEFAULT 0 CHECK (vales_revisados >= 0),
    diferencias         integer NOT NULL DEFAULT 0 CHECK (diferencias >= 0),
    creado_en           timestamptz NOT NULL DEFAULT now()
);

-- ---
CREATE TABLE IF NOT EXISTS diferencias_integridad (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verificacion_id     bigint NOT NULL REFERENCES verificaciones_integridad(id) ON DELETE RESTRICT,
    vale_id             bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    saldo_almacenado    numeric(12,2) NOT NULL,
    saldo_recalculado   numeric(12,2) NOT NULL,
    revisada            boolean NOT NULL DEFAULT false,
    revisada_por        bigint REFERENCES app_users(id) ON DELETE RESTRICT,
    revisada_en         timestamptz,
    comentario          text,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT diferencias_revisada_comentario CHECK (NOT revisada OR nullif(trim(comentario), '') IS NOT NULL)
);

-- ---
CREATE INDEX IF NOT EXISTS ix_diferencias_pendientes ON diferencias_integridad (revisada, creado_en DESC) WHERE NOT revisada;

-- ---
CREATE INDEX IF NOT EXISTS ix_diferencias_vale ON diferencias_integridad (vale_id, creado_en DESC);

-- ---
CREATE TABLE IF NOT EXISTS impresiones_vale (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vale_id         bigint NOT NULL REFERENCES vales(id) ON DELETE RESTRICT,
    app_user_id     bigint NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    es_duplicado    boolean NOT NULL DEFAULT false,
    creado_en       timestamptz NOT NULL DEFAULT now()
);

-- ---
CREATE INDEX IF NOT EXISTS ix_impresiones_vale_fecha ON impresiones_vale (vale_id, creado_en DESC);

-- ---
-- Disparadores que garantizan la inalterabilidad incluso para el dueño.
CREATE OR REPLACE FUNCTION rechazar_mutacion_inmutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'La tabla %.% es inmutable', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

-- ---
DROP TRIGGER IF EXISTS movimientos_vale_inmutables ON movimientos_vale;

-- ---
CREATE TRIGGER movimientos_vale_inmutables
BEFORE UPDATE OR DELETE ON movimientos_vale
FOR EACH ROW EXECUTE FUNCTION rechazar_mutacion_inmutable();

-- ---
DROP TRIGGER IF EXISTS auditoria_inmutable ON auditoria;

-- ---
CREATE TRIGGER auditoria_inmutable
BEFORE UPDATE OR DELETE ON auditoria
FOR EACH ROW EXECUTE FUNCTION rechazar_mutacion_inmutable();

-- ---
CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$;

-- ---
DO $$
DECLARE tabla text;
BEGIN
    FOREACH tabla IN ARRAY ARRAY['estaciones', 'app_users', 'combustibles', 'instituciones', 'ordenes_compra', 'ocr_extracciones', 'vales'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I_actualizado_en ON %I', tabla, tabla);
        EXECUTE format('CREATE TRIGGER %I_actualizado_en BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp()', tabla, tabla);
    END LOOP;
END $$;

-- ---
-- Permisos mínimos: el dono del esquema tiene el DDL; `vales_app` es runtime.
GRANT USAGE ON SCHEMA public TO vales_app;

-- ---
GRANT SELECT, INSERT, UPDATE ON
    estaciones, app_users, refresh_tokens, intentos_login, tokens_recuperacion,
    parametros, combustibles, precios_combustible, instituciones,
    ordenes_compra, ocr_extracciones, secuencias, vales,
    verificaciones_integridad, diferencias_integridad, impresiones_vale
TO vales_app;

-- ---
GRANT SELECT, INSERT ON movimientos_vale, auditoria TO vales_app;

-- ---
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vales_app;

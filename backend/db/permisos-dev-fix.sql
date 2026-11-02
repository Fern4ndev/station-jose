-- ============================================================================
-- Corrección de permisos para la base de desarrollo `sanjose` (una sola vez).
-- V2: SIN transacción explícita (cada instrucción por separado, para que un
-- fallo no deje la transacción rota y podamos ver el error real).
--
-- CÓMO USARLO:
--   1. pgAdmin 4, conectado como superusuario `postgres`.
--   2. Base activa: `sanjose`.
--   3. Si al ejecutar TODO el bloque vuelve a fallar, ejecuta las instrucciones
--      UNA POR UNA y avísanos cuál y qué error fue EL PRIMERO (pestaña
--      "Messages", el mensaje rojo más arriba, no el 25P02 final).
-- ============================================================================

-- 1. El esquema pasa a ser de vales_migrador (esta es la que daba el
--    "permission denied for schema public").
ALTER SCHEMA public OWNER TO vales_migrador;

-- 2. Toda tabla que siga en propiedad de otro rol pasa a vales_migrador.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tableowner IS DISTINCT FROM 'vales_migrador'
    LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO vales_migrador', r.tablename);
    END LOOP;

    -- Secuencias (identidades grandes de las tablas).
    FOR r IN
        SELECT sequencename FROM pg_sequences
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO vales_migrador', r.sequencename);
    END LOOP;

    -- Funciones y disparadores asociados (migración 0001).
    FOR r IN
        SELECT p.proname AS nombre,
               pg_get_function_identity_arguments(p.oid) AS argumentos
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prokind = 'f'
    LOOP
        EXECUTE format('ALTER FUNCTION public.%I(%s) OWNER TO vales_migrador',
                       r.nombre, r.argumentos);
    END LOOP;
END
$$;

-- 3. Permisos mínimos para el rol de la aplicación, como describe el README.
GRANT CONNECT ON DATABASE sanjose TO vales_migrador, vales_app;
GRANT USAGE ON SCHEMA public TO vales_app;

-- 4. Verificación: debe listar TODO con tableowner = vales_migrador
--    (descomenta para ejecutar).
-- SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';

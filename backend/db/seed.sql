-- Datos iniciales de demostración. No ejecutar en producción.
-- Requisitos: ejecutar schema.sql y crear primero un administrador válido desde
-- la aplicación, por ejemplo: python -m app.cli crear-admin --nombre Admin --correo admin@ejemplo.pe
-- Las contraseñas nunca se crean ni se guardan desde este archivo SQL.
--
-- Ejecutar desde la raíz del proyecto:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/db/seed.sql
-- Es idempotente: no duplica estaciones, catálogos, órdenes, vales ni movimientos.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.estaciones') IS NULL
       OR to_regclass('public.usuarios') IS NULL
       OR to_regclass('public.instituciones') IS NULL
       OR to_regclass('public.ordenes_compra') IS NULL
       OR to_regclass('public.vales') IS NULL
       OR to_regclass('public.movimientos_vale') IS NULL THEN
        RAISE EXCEPTION 'Falta el esquema. Ejecuta primero backend/db/schema.sql.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM usuarios WHERE rol = 'administrador' AND activo
    ) THEN
        RAISE EXCEPTION 'Crea un usuario Administrador activo desde la aplicación antes de ejecutar el seed.';
    END IF;
END;
$$;

INSERT INTO estaciones (nombre, ruc, direccion, telefono, correo)
SELECT v.nombre, v.ruc, v.direccion, v.telefono, v.correo
FROM (VALUES
    ('San José - Abancay', '20555555556', 'Av. Núñez del Prado 123, Abancay', '083-321001', 'abancay@grsanjose.pe'),
    ('San José - Tamburco', '20555555556', 'Av. Tamburco s/n, Abancay', '083-321002', 'tamburco@gr sanjose.pe')
) AS v(nombre, ruc, direccion, telefono, correo)
WHERE NOT EXISTS (SELECT 1 FROM estaciones e WHERE lower(e.nombre) = lower(v.nombre));

INSERT INTO parametros (clave, valor)
VALUES
    ('ocr_umbral_confianza', '0.80'),
    ('archivo_max_mb', '10'),
    ('vale_formato_codigo', 'VAL-{anio}-{secuencia:06d}'),
    ('vale_vigencia_dias', ''),
    ('vale_umbral_saldo_bajo_pct', '10'),
    ('vale_dias_aviso_vencimiento', '7'),
    ('login_intentos_max', '5'),
    ('login_bloqueo_min', '15'),
    ('refresh_token_dias', '30')
ON CONFLICT (clave) DO NOTHING;

INSERT INTO combustibles (nombre)
VALUES ('Diésel B5'), ('Gasohol 90'), ('Gasohol 95'), ('GLP')
ON CONFLICT DO NOTHING;

INSERT INTO precios_combustible (combustible_id, precio_galon, vigente_desde, usuario_id)
SELECT c.id, v.precio, v.vigente_desde, u.id
FROM (VALUES
    ('Diésel B5',  15.20::numeric, DATE '2026-09-01'),
    ('Diésel B5',  15.80::numeric, DATE '2026-10-15'),
    ('Gasohol 90', 16.50::numeric, DATE '2026-09-01'),
    ('Gasohol 90', 17.10::numeric, DATE '2026-10-15'),
    ('Gasohol 95', 17.50::numeric, DATE '2026-09-01'),
    ('Gasohol 95', 18.20::numeric, DATE '2026-10-15'),
    ('GLP',          8.90::numeric, DATE '2026-09-01'),
    ('GLP',          9.30::numeric, DATE '2026-10-15')
) AS v(combustible, precio, vigente_desde)
JOIN combustibles c ON c.nombre = v.combustible
CROSS JOIN LATERAL (
    SELECT id FROM usuarios WHERE rol = 'administrador' AND activo ORDER BY id LIMIT 1
) u
ON CONFLICT (combustible_id, vigente_desde) DO NOTHING;

INSERT INTO instituciones (
    nombre, ruc, tipo, telefono, correo, direccion, representante,
    modalidad_numeracion
)
VALUES
    ('Municipalidad Provincial de Abancay', '20111111112', 'publica', '083-321101', 'compras@muniabancay.gob.pe', 'Jr. Puno 200, Abancay', 'Juan Pérez', 'general'),
    ('Empresa de Transportes Los Andes S.A.C.', '20222222223', 'privada', '083-322202', 'logistica@transporteslosandes.pe', 'Av. Los Andes 450, Abancay', 'María Quispe', 'por_orden'),
    ('ONG Semilla Andina', '20333333334', 'ong', '083-323303', 'proyectos@semillaandina.org', 'Calle Cusco 315, Abancay', 'Carlos Huamán', 'no_aplica'),
    ('Instituto Tecnológico de Abancay', '20444444445', 'publica', '083-324404', 'administracion@ita.edu.pe', 'Av. Tecnológico 100, Abancay', 'Rosa Salas', 'general')
ON CONFLICT (ruc) DO NOTHING;

INSERT INTO ordenes_compra (
    institucion_id, numero, anio, fecha_emision, presupuesto_soles,
    combustible_id, estado, serie_desde, serie_hasta, creada_con_ocr,
    observaciones, motivo_anulacion, creado_por
)
SELECT i.id, v.numero, v.anio, v.fecha_emision, v.presupuesto,
       c.id, v.estado, v.serie_desde, v.serie_hasta, false,
       v.observaciones, v.motivo_anulacion, u.id
FROM (VALUES
    ('20111111112', 'OC-001-2026', 2026, DATE '2026-10-01', 15000.00::numeric, 'Diésel B5', 'vigente', 1, 100, 'Orden vigente para pruebas de despacho', NULL::text),
    ('20111111112', 'OC-002-2026', 2026, DATE '2026-10-05',  8000.00::numeric, 'Gasohol 90', 'borrador', NULL::integer, NULL::integer, 'Orden en borrador', NULL::text),
    ('20222222223', 'OC-010-2026', 2026, DATE '2026-10-03',  5000.00::numeric, 'Gasohol 95', 'vigente', 1, 50, 'Orden con numeración por orden', NULL::text),
    ('20333333334', 'OC-020-2026', 2026, DATE '2026-10-10',  3000.00::numeric, 'GLP', 'cerrada', NULL::integer, NULL::integer, 'Orden cerrada de demostración', NULL::text),
    ('20444444445', 'OC-030-2026', 2026, DATE '2026-09-20', 12000.00::numeric, 'Diésel B5', 'anulada', NULL::integer, NULL::integer, 'Orden anulada de demostración', 'Anulada para probar el estado')
) AS v(ruc, numero, anio, fecha_emision, presupuesto, combustible, estado,
        serie_desde, serie_hasta, observaciones, motivo_anulacion)
JOIN instituciones i ON i.ruc = v.ruc
LEFT JOIN combustibles c ON c.nombre = v.combustible
CROSS JOIN LATERAL (
    SELECT id FROM usuarios WHERE rol = 'administrador' AND activo ORDER BY id LIMIT 1
) u
ON CONFLICT (institucion_id, anio, numero) DO NOTHING;

DO $$
DECLARE
    admin_id bigint;
    estacion_abancay_id bigint;
    estacion_tamburco_id bigint;
    orden_diesel_id bigint;
    orden_gasohol_id bigint;
    diesel_id bigint;
    gasohol_id bigint;
    vale_id bigint;
BEGIN
    SELECT id INTO admin_id FROM usuarios WHERE rol = 'administrador' AND activo ORDER BY id LIMIT 1;
    SELECT id INTO estacion_abancay_id FROM estaciones WHERE nombre = 'San José - Abancay';
    SELECT id INTO estacion_tamburco_id FROM estaciones WHERE nombre = 'San José - Tamburco';
    SELECT id INTO diesel_id FROM combustibles WHERE nombre = 'Diésel B5';
    SELECT id INTO gasohol_id FROM combustibles WHERE nombre = 'Gasohol 95';

    SELECT o.id INTO orden_diesel_id
      FROM ordenes_compra o JOIN instituciones i ON i.id = o.institucion_id
     WHERE i.ruc = '20111111112' AND o.numero = 'OC-001-2026' AND o.anio = 2026;
    SELECT o.id INTO orden_gasohol_id
      FROM ordenes_compra o JOIN instituciones i ON i.id = o.institucion_id
     WHERE i.ruc = '20222222223' AND o.numero = 'OC-010-2026' AND o.anio = 2026;

    IF admin_id IS NULL OR estacion_abancay_id IS NULL OR estacion_tamburco_id IS NULL
       OR diesel_id IS NULL OR gasohol_id IS NULL OR orden_diesel_id IS NULL OR orden_gasohol_id IS NULL THEN
        RAISE EXCEPTION 'No se encontraron los datos base requeridos para sembrar vales.';
    END IF;

    -- Vale de estación para probar consumo desde cualquiera de las sedes.
    INSERT INTO vales (
        codigo_interno, orden_compra_id, emisor, combustible_id,
        cantidad_inicial, precio_galon_aplicado, valor_soles,
        valor_comprometido_soles, saldo, estado, fecha_emision,
        fecha_vencimiento, creado_por
    ) VALUES (
        'VAL-2026-000001', orden_diesel_id, 'estacion', diesel_id,
        100.00, 15.80, 1580.00, 1580.00, 100.00, 'activo',
        DATE '2026-10-16', DATE '2026-12-31', admin_id
    ) ON CONFLICT (codigo_interno) DO NOTHING;

    SELECT id INTO vale_id FROM vales WHERE codigo_interno = 'VAL-2026-000001';
    IF NOT EXISTS (SELECT 1 FROM movimientos_vale mv WHERE mv.vale_id = vale_id AND mv.tipo = 'emision') THEN
        INSERT INTO movimientos_vale (
            vale_id, tipo, variacion, saldo_posterior, usuario_id, estacion_id,
            motivo, fecha_local
        ) VALUES (
            vale_id, 'emision', 100.00, 100.00, admin_id, estacion_abancay_id,
            'Seed: emisión de demostración', DATE '2026-10-16'
        );
    END IF;

    -- Vale con consumo de 100 soles en la segunda sede: precio 15.80/galón,
    -- equivalente a 6.33 galones (redondeo a dos decimales), saldo 43.67.
    INSERT INTO vales (
        codigo_interno, orden_compra_id, emisor, combustible_id,
        cantidad_inicial, precio_galon_aplicado, valor_soles,
        valor_comprometido_soles, saldo, estado, fecha_emision,
        fecha_vencimiento, creado_por
    ) VALUES (
        'VAL-2026-000002', orden_diesel_id, 'estacion', diesel_id,
        50.00, 15.80, 790.00, 790.00, 43.67, 'activo',
        DATE '2026-10-16', DATE '2026-12-31', admin_id
    ) ON CONFLICT (codigo_interno) DO NOTHING;

    SELECT id INTO vale_id FROM vales WHERE codigo_interno = 'VAL-2026-000002';
    IF NOT EXISTS (SELECT 1 FROM movimientos_vale WHERE movimientos_vale.vale_id = vale_id AND tipo = 'emision') THEN
        INSERT INTO movimientos_vale (
            vale_id, tipo, variacion, saldo_posterior, usuario_id, estacion_id,
            motivo, fecha_local
        ) VALUES (
            vale_id, 'emision', 50.00, 50.00, admin_id, estacion_abancay_id,
            'Seed: emisión de demostración', DATE '2026-10-16'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM movimientos_vale WHERE token_operacion = '00000000-0000-4000-8000-000000000002') THEN
        INSERT INTO movimientos_vale (
            vale_id, tipo, variacion, saldo_posterior, cantidad_galones,
            precio_galon, importe_soles, usuario_id, estacion_id, motivo,
            placa, conductor, token_operacion, fecha_local
        ) VALUES (
            vale_id, 'consumo', -6.33, 43.67, 6.33, 15.80, 100.00,
            admin_id, estacion_tamburco_id, 'Seed: consumo de demostración de S/ 100.00',
            'ABC-123', 'Luis Quispe', '00000000-0000-4000-8000-000000000002', DATE '2026-10-17'
        );
    END IF;

    -- Vale emitido por la entidad; clave única para su numeración por orden.
    INSERT INTO vales (
        codigo_interno, numero_entidad, clave_numeracion, orden_compra_id,
        emisor, combustible_id, cantidad_inicial, precio_galon_aplicado,
        valor_soles, valor_comprometido_soles, saldo, estado,
        fecha_emision, fecha_vencimiento, creado_por
    ) VALUES (
        'VAL-2026-000003', '0001', 'orden:' || orden_gasohol_id::text || ':0001',
        orden_gasohol_id, 'entidad', gasohol_id, 20.00, 18.20,
        364.00, 364.00, 20.00, 'activo', DATE '2026-10-17', DATE '2026-12-31', admin_id
    ) ON CONFLICT (codigo_interno) DO NOTHING;

    SELECT id INTO vale_id FROM vales WHERE codigo_interno = 'VAL-2026-000003';
    IF NOT EXISTS (SELECT 1 FROM movimientos_vale WHERE movimientos_vale.vale_id = vale_id AND tipo = 'emision') THEN
        INSERT INTO movimientos_vale (
            vale_id, tipo, variacion, saldo_posterior, usuario_id, estacion_id,
            motivo, fecha_local
        ) VALUES (
            vale_id, 'emision', 20.00, 20.00, admin_id, estacion_abancay_id,
            'Seed: emisión de vale de entidad', DATE '2026-10-17'
        );
    END IF;

    INSERT INTO secuencias (nombre, anio, ultimo)
    VALUES ('vale', 2026, 3)
    ON CONFLICT (nombre, anio) DO UPDATE
       SET ultimo = GREATEST(secuencias.ultimo, EXCLUDED.ultimo);
END;
$$;

COMMIT;

-- Consultas manuales opcionales de comprobación:
-- SELECT rol, count(*) FROM usuarios GROUP BY rol ORDER BY rol;
-- SELECT codigo_interno, saldo,
--        (SELECT COALESCE(sum(m.variacion), 0) FROM movimientos_vale m WHERE m.vale_id = v.id) AS saldo_movimientos
-- FROM vales v ORDER BY codigo_interno;
-- SELECT e.nombre AS estacion, m.tipo, m.importe_soles, m.cantidad_galones, m.creado_en
-- FROM movimientos_vale m JOIN estaciones e ON e.id = m.estacion_id
-- ORDER BY m.creado_en;

-- Datos de demostración para desarrollo; no ejecutar en producción.
-- Inserta al menos un registro en cada tabla del esquema.
-- Las cuentas demo están deshabilitadas y no tienen credenciales de acceso.
-- DEMO-DIESEL-S50 es un valor ilustrativo, no el catálogo aprobado.

BEGIN;

INSERT INTO branches (id, code, name)
VALUES
    ('10000000-0000-4000-8000-000000000001', 'SAN_JOSE', 'San José'),
    ('10000000-0000-4000-8000-000000000002', 'SANTA_MARTA', 'Santa Marta')
ON CONFLICT (code) DO NOTHING;

INSERT INTO users (
    id, first_name, last_name, dni, email, password_hash, role, branch_id, is_active
)
VALUES
    (
        '20000000-0000-4000-8000-000000000001',
        'Admin', 'Demo', NULL, 'admin@example.test',
        'seed-disabled-no-login', 'ADMIN', NULL, FALSE
    ),
    (
        '20000000-0000-4000-8000-000000000002',
        'Oficina', 'Demo', '76548234', 'office@example.test',
        'seed-disabled-no-login', 'OFFICE',
        (SELECT id FROM branches WHERE code = 'SAN_JOSE'), FALSE
    ),
    (
        '20000000-0000-4000-8000-000000000003',
        'Grifero', 'Demo', '76548234', 'attendant@example.test',
        'seed-disabled-no-login', 'ATTENDANT',
        (SELECT id FROM branches WHERE code = 'SAN_JOSE'), FALSE
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO auth_sessions (id, user_id, jti, expires_at, revoked_at, created_at)
VALUES (
    '30000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000003',
    'seed-demo-revoked-session',
    '2025-01-01 00:00:00+00',
    '2024-12-31 00:00:00+00',
    '2024-12-30 00:00:00+00'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO fuel_types (id, code, name, is_active)
VALUES (
    '40000000-0000-4000-8000-000000000001',
    'DEMO-DIESEL-S50',
    'Diesel S50 (demo)',
    FALSE
)
ON CONFLICT (code) DO NOTHING;

INSERT INTO purchase_orders (
    id, order_number, siaf_number, issue_date, institution_name, supplier_name,
    supplier_details, executing_unit, executing_unit_ruc, branch_id
)
VALUES (
    '50000000-0000-4000-8000-000000000001',
    'DEMO-OC-001',
    'DEMO-SIAF-001',
    '2024-12-01',
    'Entidad de demostración',
    'Estación de Servicio San José',
    'Registro ficticio para desarrollo.',
    'Unidad ejecutora de demostración',
    '00000000000',
    (SELECT id FROM branches WHERE code = 'SAN_JOSE')
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO purchase_order_items (
    id, purchase_order_id, fuel_type_id, authorized_gallons, unit_price, total_amount
)
VALUES (
    '60000000-0000-4000-8000-000000000001',
    '50000000-0000-4000-8000-000000000001',
    (SELECT id FROM fuel_types WHERE code = 'DEMO-DIESEL-S50'),
    10.000,
    15.2500,
    152.50
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO vouchers (
    id, purchase_order_id, issuer_type, issuer_name, issuer_normalized,
    voucher_number, voucher_number_normalized
)
VALUES (
    '70000000-0000-4000-8000-000000000001',
    '50000000-0000-4000-8000-000000000001',
    'INSTITUTION',
    'Entidad de demostración',
    'entidad de demostracion',
    'DEMO-VALE-001',
    'DEMO-VALE-001'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO voucher_items (
    id, voucher_id, purchase_order_id, purchase_order_item_id, authorized_gallons
)
VALUES (
    '80000000-0000-4000-8000-000000000001',
    '70000000-0000-4000-8000-000000000001',
    '50000000-0000-4000-8000-000000000001',
    '60000000-0000-4000-8000-000000000001',
    10.000
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO attendances (
    id, voucher_id, performed_by_user_id, branch_id, attended_at,
    idempotency_key, request_fingerprint
)
VALUES (
    '90000000-0000-4000-8000-000000000001',
    '70000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000003',
    (SELECT id FROM branches WHERE code = 'SAN_JOSE'),
    '2024-12-15 10:00:00+00',
    'a0000000-0000-4000-8000-000000000001',
    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO attendance_items (
    id, attendance_id, voucher_id, voucher_item_id, attended_gallons,
    unit_price_snapshot, attended_amount
)
VALUES (
    'b0000000-0000-4000-8000-000000000001',
    '90000000-0000-4000-8000-000000000001',
    '70000000-0000-4000-8000-000000000001',
    '80000000-0000-4000-8000-000000000001',
    5.000,
    15.2500,
    76.25
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO attendance_verifications (
    id, attendance_id, reviewed_by_user_id, decision, observation, reviewed_at
)
VALUES (
    'c0000000-0000-4000-8000-000000000001',
    '90000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000002',
    'VERIFIED',
    NULL,
    '2024-12-16 12:00:00+00'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO document_counters (id, counter_code, last_value)
VALUES (
    'd0000000-0000-4000-8000-000000000001',
    'DEMO-STATION-VOUCHER',
    1
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

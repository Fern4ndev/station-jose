-- Esquema inicial PostgreSQL para Estación de Servicio San José.
-- Las unicidades de órdenes (PD-001) y vales (PD-002) quedan pendientes
-- de aprobación y no se imponen aquí.

BEGIN;

CREATE TABLE branches (
    id UUID PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT branches_code_not_blank CHECK (btrim(code) <> ''),
    CONSTRAINT branches_name_not_blank CHECK (btrim(name) <> '')
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    dni VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    branch_id UUID,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_role_check CHECK (role IN ('ADMIN', 'OFFICE', 'ATTENDANT')),
    CONSTRAINT users_attendant_branch_check
        CHECK (role <> 'ATTENDANT' OR branch_id IS NOT NULL),
    CONSTRAINT users_office_branch_check
        CHECK (role <> 'OFFICE' OR branch_id IS NULL),
    CONSTRAINT users_first_name_not_blank CHECK (btrim(first_name) <> ''),
    CONSTRAINT users_last_name_not_blank CHECK (btrim(last_name) <> ''),
    CONSTRAINT users_dni_not_blank CHECK (btrim(dni) <> ''),
    CONSTRAINT users_email_not_blank CHECK (btrim(email) <> ''),
    CONSTRAINT users_password_hash_not_blank CHECK (btrim(password_hash) <> ''),
    CONSTRAINT users_branch_fk
        FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE RESTRICT
);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    jti VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT auth_sessions_jti_not_blank CHECK (btrim(jti) <> ''),
    CONSTRAINT auth_sessions_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE fuel_types (
    id UUID PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fuel_types_code_not_blank CHECK (btrim(code) <> ''),
    CONSTRAINT fuel_types_name_not_blank CHECK (btrim(name) <> '')
);

CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY,
    order_number VARCHAR(60) NOT NULL,
    siaf_number VARCHAR(60) NOT NULL,
    issue_date DATE NOT NULL,
    institution_name VARCHAR(200) NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    supplier_details TEXT,
    executing_unit VARCHAR(200) NOT NULL,
    executing_unit_ruc VARCHAR(20) NOT NULL,
    branch_id UUID NOT NULL,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT purchase_orders_order_number_not_blank CHECK (btrim(order_number) <> ''),
    CONSTRAINT purchase_orders_siaf_number_not_blank CHECK (btrim(siaf_number) <> ''),
    CONSTRAINT purchase_orders_institution_not_blank CHECK (btrim(institution_name) <> ''),
    CONSTRAINT purchase_orders_supplier_not_blank CHECK (btrim(supplier_name) <> ''),
    CONSTRAINT purchase_orders_executing_unit_not_blank CHECK (btrim(executing_unit) <> ''),
    CONSTRAINT purchase_orders_ruc_not_blank CHECK (btrim(executing_unit_ruc) <> ''),
    CONSTRAINT purchase_orders_branch_fk
        FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE RESTRICT
);

CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY,
    purchase_order_id UUID NOT NULL,
    fuel_type_id UUID NOT NULL,
    authorized_gallons NUMERIC(14, 3) NOT NULL,
    unit_price NUMERIC(14, 4) NOT NULL,
    total_amount NUMERIC(14, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT purchase_order_items_gallons_positive CHECK (authorized_gallons > 0),
    CONSTRAINT purchase_order_items_unit_price_nonnegative CHECK (unit_price >= 0),
    CONSTRAINT purchase_order_items_total_nonnegative CHECK (total_amount >= 0),
    CONSTRAINT purchase_order_items_id_order_unique UNIQUE (id, purchase_order_id),
    CONSTRAINT purchase_order_items_order_fk
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders (id) ON DELETE RESTRICT,
    CONSTRAINT purchase_order_items_fuel_type_fk
        FOREIGN KEY (fuel_type_id) REFERENCES fuel_types (id) ON DELETE RESTRICT
);

CREATE TABLE vouchers (
    id UUID PRIMARY KEY,
    purchase_order_id UUID NOT NULL,
    issuer_type VARCHAR(20) NOT NULL,
    issuer_name VARCHAR(200) NOT NULL,
    issuer_normalized VARCHAR(200) NOT NULL,
    voucher_number VARCHAR(60) NOT NULL,
    voucher_number_normalized VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT vouchers_issuer_type_check
        CHECK (issuer_type IN ('INSTITUTION', 'STATION')),
    CONSTRAINT vouchers_issuer_name_not_blank CHECK (btrim(issuer_name) <> ''),
    CONSTRAINT vouchers_issuer_normalized_not_blank CHECK (btrim(issuer_normalized) <> ''),
    CONSTRAINT vouchers_number_not_blank CHECK (btrim(voucher_number) <> ''),
    CONSTRAINT vouchers_number_normalized_not_blank
        CHECK (btrim(voucher_number_normalized) <> ''),
    CONSTRAINT vouchers_id_order_unique UNIQUE (id, purchase_order_id),
    CONSTRAINT vouchers_identity_unique
        UNIQUE (purchase_order_id, issuer_normalized, voucher_number_normalized),
    CONSTRAINT vouchers_purchase_order_fk
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders (id) ON DELETE RESTRICT
);

CREATE TABLE voucher_items (
    id UUID PRIMARY KEY,
    voucher_id UUID NOT NULL,
    purchase_order_id UUID NOT NULL,
    purchase_order_item_id UUID NOT NULL,
    authorized_gallons NUMERIC(14, 3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT voucher_items_gallons_positive CHECK (authorized_gallons > 0),
    CONSTRAINT voucher_items_voucher_order_unique UNIQUE (voucher_id, purchase_order_item_id),
    CONSTRAINT voucher_items_id_voucher_unique UNIQUE (id, voucher_id),
    CONSTRAINT voucher_items_voucher_order_fk
        FOREIGN KEY (voucher_id, purchase_order_id)
        REFERENCES vouchers (id, purchase_order_id) ON DELETE RESTRICT,
    CONSTRAINT voucher_items_order_item_fk
        FOREIGN KEY (purchase_order_item_id, purchase_order_id)
        REFERENCES purchase_order_items (id, purchase_order_id) ON DELETE RESTRICT
);

CREATE TABLE attendances (
    id UUID PRIMARY KEY,
    voucher_id UUID NOT NULL,
    performed_by_user_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    attended_at TIMESTAMPTZ NOT NULL,
    idempotency_key UUID NOT NULL UNIQUE,
    request_fingerprint VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT attendances_request_fingerprint_not_blank
        CHECK (btrim(request_fingerprint) <> ''),
    CONSTRAINT attendances_id_voucher_unique UNIQUE (id, voucher_id),
    CONSTRAINT attendances_voucher_fk
        FOREIGN KEY (voucher_id) REFERENCES vouchers (id) ON DELETE RESTRICT,
    CONSTRAINT attendances_performed_by_fk
        FOREIGN KEY (performed_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT attendances_branch_fk
        FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE RESTRICT
);

CREATE TABLE attendance_items (
    id UUID PRIMARY KEY,
    attendance_id UUID NOT NULL,
    voucher_id UUID NOT NULL,
    voucher_item_id UUID NOT NULL,
    attended_gallons NUMERIC(14, 3) NOT NULL,
    unit_price_snapshot NUMERIC(14, 4) NOT NULL,
    attended_amount NUMERIC(14, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT attendance_items_gallons_positive CHECK (attended_gallons > 0),
    CONSTRAINT attendance_items_unit_price_nonnegative CHECK (unit_price_snapshot >= 0),
    CONSTRAINT attendance_items_amount_nonnegative CHECK (attended_amount >= 0),
    CONSTRAINT attendance_items_attendance_voucher_unique
        UNIQUE (attendance_id, voucher_item_id),
    CONSTRAINT attendance_items_attendance_voucher_fk
        FOREIGN KEY (attendance_id, voucher_id)
        REFERENCES attendances (id, voucher_id) ON DELETE RESTRICT,
    CONSTRAINT attendance_items_voucher_item_fk
        FOREIGN KEY (voucher_item_id, voucher_id)
        REFERENCES voucher_items (id, voucher_id) ON DELETE RESTRICT
);

CREATE TABLE attendance_verifications (
    id UUID PRIMARY KEY,
    attendance_id UUID NOT NULL,
    reviewed_by_user_id UUID NOT NULL,
    decision VARCHAR(20) NOT NULL,
    observation TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT attendance_verifications_decision_check
        CHECK (decision IN ('VERIFIED', 'OBSERVED')),
    CONSTRAINT attendance_verifications_observation_check
        CHECK (decision <> 'OBSERVED' OR NULLIF(btrim(observation), '') IS NOT NULL),
    CONSTRAINT attendance_verifications_attendance_fk
        FOREIGN KEY (attendance_id) REFERENCES attendances (id) ON DELETE RESTRICT,
    CONSTRAINT attendance_verifications_reviewer_fk
        FOREIGN KEY (reviewed_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE document_counters (
    id UUID PRIMARY KEY,
    counter_code VARCHAR(40) NOT NULL UNIQUE,
    last_value BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT document_counters_last_value_nonnegative CHECK (last_value >= 0),
    CONSTRAINT document_counters_code_not_blank CHECK (btrim(counter_code) <> '')
);

CREATE INDEX users_branch_id_idx ON users (branch_id);
CREATE INDEX auth_sessions_user_expires_idx ON auth_sessions (user_id, expires_at);
CREATE INDEX purchase_orders_issue_date_idx ON purchase_orders (issue_date);
CREATE INDEX purchase_orders_order_number_idx ON purchase_orders (order_number);
CREATE INDEX purchase_orders_executing_unit_ruc_idx ON purchase_orders (executing_unit_ruc);
CREATE INDEX purchase_orders_institution_name_idx ON purchase_orders (institution_name);
CREATE INDEX purchase_orders_branch_id_idx ON purchase_orders (branch_id);
CREATE INDEX purchase_order_items_order_id_idx ON purchase_order_items (purchase_order_id);
CREATE INDEX purchase_order_items_fuel_type_id_idx ON purchase_order_items (fuel_type_id);
CREATE INDEX vouchers_order_id_idx ON vouchers (purchase_order_id);
CREATE INDEX vouchers_lookup_idx
    ON vouchers (purchase_order_id, issuer_type, issuer_normalized, voucher_number_normalized);
CREATE INDEX voucher_items_voucher_order_idx ON voucher_items (voucher_id, purchase_order_id);
CREATE INDEX voucher_items_order_item_idx
    ON voucher_items (purchase_order_item_id, purchase_order_id);
CREATE INDEX attendances_voucher_attended_at_idx ON attendances (voucher_id, attended_at);
CREATE INDEX attendances_user_attended_at_idx
    ON attendances (performed_by_user_id, attended_at);
CREATE INDEX attendances_branch_attended_at_idx ON attendances (branch_id, attended_at);
CREATE INDEX attendance_items_attendance_voucher_idx ON attendance_items (attendance_id, voucher_id);
CREATE INDEX attendance_items_voucher_item_idx ON attendance_items (voucher_item_id, voucher_id);
CREATE INDEX attendance_verifications_attendance_reviewed_idx
    ON attendance_verifications (attendance_id, reviewed_at DESC);
CREATE INDEX attendance_verifications_reviewer_id_idx
    ON attendance_verifications (reviewed_by_user_id);

COMMIT;

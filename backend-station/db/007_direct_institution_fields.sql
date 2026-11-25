BEGIN;

ALTER TABLE purchase_orders
    DROP CONSTRAINT IF EXISTS purchase_orders_institution_fk;

DROP INDEX IF EXISTS purchase_orders_institution_id_idx;

ALTER TABLE purchase_orders
    DROP COLUMN IF EXISTS institution_id;

DROP TABLE IF EXISTS institutions;

CREATE INDEX IF NOT EXISTS purchase_orders_executing_unit_ruc_idx
    ON purchase_orders (executing_unit_ruc);

COMMIT;

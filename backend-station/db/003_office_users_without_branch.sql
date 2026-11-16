-- Las cuentas OFFICE administran ambas sedes y no pertenecen a una sede específica.

BEGIN;

UPDATE users
SET branch_id = NULL
WHERE role = 'OFFICE'
  AND branch_id IS NOT NULL;

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_office_branch_check;

ALTER TABLE users
    ADD CONSTRAINT users_office_branch_check
    CHECK (role <> 'OFFICE' OR branch_id IS NULL);

COMMIT;

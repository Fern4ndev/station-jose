-- El administrador es una cuenta global y única. No elimina cuentas existentes.
-- Si hay más de un ADMIN, resolverlos manualmente antes de aplicar esta migración.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM users
        WHERE role = 'ADMIN'
        GROUP BY role
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Hay más de una cuenta ADMIN; resuelve los duplicados antes de continuar.'
            USING HINT = 'Conserva un único ADMIN y cambia los demás a OFFICE o ATTENDANT.';
    END IF;
END;
$$;

UPDATE users
SET branch_id = NULL
WHERE role = 'ADMIN'
  AND branch_id IS NOT NULL;

ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_admin_branch_check;

ALTER TABLE users
    ADD CONSTRAINT users_admin_branch_check
    CHECK (role <> 'ADMIN' OR branch_id IS NULL);

CREATE UNIQUE INDEX IF NOT EXISTS users_single_admin_idx
    ON users (role)
    WHERE role = 'ADMIN';

COMMIT;

-- Retira la verificación administrativa, fuera del alcance desde el 20/11/2026.
-- Elimina la tabla y sus índices; el contenido que aún exista se pierde.
-- Es re-ejecutable: si la tabla y los índices ya no existen, no hace nada.
--
-- Aplicar solo después de comprobar que no quedan dependencias en routers,
-- servicios, schemas ni pruebas. Al consolidar el cambio hay que quitar la tabla
-- de 001_schema.sql, sus INSERT de 002_seed.sql y el modelo AttendanceVerification
-- de app/tables.py (incluidas las relaciones User.verifications y
-- Attendance.verifications).

BEGIN;

DROP INDEX IF EXISTS attendance_verifications_attendance_reviewed_idx;
DROP INDEX IF EXISTS attendance_verifications_reviewer_id_idx;

DROP TABLE IF EXISTS attendance_verifications;

COMMIT;

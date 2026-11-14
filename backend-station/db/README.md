# Base de datos

PostgreSQL es el motor de persistencia del backend. Alembic será la fuente
versionada del esquema y de los cambios posteriores.

- [`schema.sql`](./schema.sql): esquema inicial para una base vacía.
- [`seed.sql`](./seed.sql): conjunto de datos de demostración con registros para
  todas las tablas. Es idempotente y solo debe usarse en desarrollo.

Las cuentas de demostración están deshabilitadas y no tienen credenciales de
acceso. El combustible de ejemplo no representa el catálogo aprobado por la
estación. Las reglas de unicidad para órdenes y vales siguen pendientes de
aprobación (PD-001 y PD-002).

# Base de datos

PostgreSQL es el motor de persistencia. El esquema se mantiene manualmente en SQL; Alembic, Flyway u otra herramienta de migraciones no forman parte del flujo aprobado.

## Regla de cambios

Una instalación nueva se prepara con dos scripts como máximo:

- `001_schema.sql`: fuente de verdad de la estructura. Debe reflejar el esquema de desarrollo, incluyendo el orden físico de las columnas.
- `002_seed.sql`: datos iniciales o de demostración, cuando el cambio afecte catálogos, parámetros, datos demo o columnas `NOT NULL` que el seed inserte.

Ambos se ejecutan sobre una base vacía. `001_schema.sql` y `002_seed.sql` no tienen que ser idempotentes a nivel de esquema.

Para una base que ya contiene datos, agrega además un ALTER numerado por cada cambio (`003_*.sql`, `004_*.sql`, etc.) y aplícalos en orden. Cada ALTER debe ser re-ejecutable y nunca recrear ni borrar datos. Usa, según corresponda, `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` o bloques `DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL; END $$`.

Cuando todo el equipo haya aplicado el ALTER:

1. Consolida sus cambios en `001_schema.sql` y, si aplica, `002_seed.sql`.
2. Elimina el archivo ALTER.
3. Registra en el commit qué archivo se consolidó y qué cambio contiene.
4. Añade el archivo eliminado, la fecha y el cambio consolidado al historial siguiente.

| Archivo ALTER eliminado | Fecha | Cambio consolidado |
| --- | --- | --- |
| No hay consolidaciones manuales registradas todavía. | — | — |

## Reglas de PostgreSQL

- `ALTER TYPE ... ADD VALUE` no debe ejecutarse dentro de la misma transacción que agrega el valor enum. Colócalo en su propio ALTER numerado.
- Actualiza siempre `001_schema.sql` en el mismo cambio de código cuando cambie el esquema (tabla, columna, índice, restricción, vista o valor enum).
- Si un ALTER agrega columnas, escríbelas al final de la definición de su tabla en `001_schema.sql` para conservar el orden físico.
- PostgreSQL no cierra el hueco físico de una columna eliminada. Después de un `DROP COLUMN`, documenta la excepción y compara columnas por nombre, tipo, nulabilidad y default, no solo el orden.
- La comparación entre una base antigua actualizada con el ALTER y una base nueva creada desde `001_schema.sql` + `002_seed.sql` es el contrato de verificación.

## Preparación de una base nueva

Desde `backend-station`, con PostgreSQL 17 instalado y `psql` disponible:

```powershell
createdb -U postgres sanjosedb
psql -U postgres -d sanjosedb -v ON_ERROR_STOP=1 -f db/001_schema.sql
psql -U postgres -d sanjosedb -v ON_ERROR_STOP=1 -f db/002_seed.sql
```

Para una base existente, aplica solo el ALTER pendiente. Ejecútalo dos veces en la base de prueba para comprobar que es re-ejecutable, por ejemplo:

```powershell
psql -U postgres -d sanjosedb -v ON_ERROR_STOP=1 -f db/003_nombre_del_cambio.sql
psql -U postgres -d sanjosedb -v ON_ERROR_STOP=1 -f db/003_nombre_del_cambio.sql
```

## Comprobación del contrato de esquema

Antes de cerrar un cambio de base de datos, compara:

1. Una base con la versión anterior de `001_schema.sql` y `002_seed.sql`, actualizada mediante el ALTER numerado dos veces.
2. Una base vacía creada con la versión nueva de `001_schema.sql` y `002_seed.sql`.
3. Los DDL resultantes de ambas bases, obtenidos con `pg_dump --schema-only --no-owner --no-acl`.

Los DDL deben coincidir. En PowerShell, genera los dos dumps y compara su contenido:

```powershell
$migrada = Join-Path $env:TEMP "schema-migrada.sql"
$nueva = Join-Path $env:TEMP "schema-nueva.sql"

pg_dump -U postgres -d sanjosedb_migrada --schema-only --no-owner --no-acl |
  Select-String -NotMatch '^\\(?:un)?restrict' |
  ForEach-Object { $_.Line } |
  Set-Content -Path $migrada -Encoding UTF8

pg_dump -U postgres -d sanjosedb_nueva --schema-only --no-owner --no-acl |
  Select-String -NotMatch '^\\(?:un)?restrict' |
  ForEach-Object { $_.Line } |
  Set-Content -Path $nueva -Encoding UTF8

Compare-Object (Get-Content $migrada) (Get-Content $nueva)
```

`Compare-Object` no debe mostrar diferencias. PostgreSQL 17 añade líneas `\restrict` y `\unrestrict` con tokens distintos en cada dump; por eso se excluyen antes de comparar. Tras comprobar la estructura, ejecuta la suite de pruebas contra la base actualizada y comprueba claves foráneas, restricciones, índices y datos iniciales afectados.

## Estado de transición del checkout

El repositorio todavía contiene `schema.sql`, `seed.sql`, la dependencia y los archivos de configuración de Alembic heredados; aún no contiene `001_schema.sql` ni `002_seed.sql`. La regla manual descrita aquí es la política aprobada para los siguientes cambios. La conversión de esos archivos y la retirada de Alembic siguen pendientes; no uses Alembic para crear o modificar el esquema.

El seed actual contiene datos de demostración para desarrollo. Las cuentas incluidas están deshabilitadas y no tienen credenciales de acceso. El catálogo de combustible de ejemplo no representa un catálogo aprobado por la estación.

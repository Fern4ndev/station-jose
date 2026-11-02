"""Ejecutor propio de migraciones SQL numeradas (Fase 1, sin Alembic).

Los archivos viven en `app/db/migraciones/` con el nombre `NNNN_descripcion.sql`
y se aplican en orden numérico, **solo hacia adelante** (la reversión se hace
con respaldo). Cada sentencia se separa de la siguiente por una línea con
`-- ---`, de modo que los cuerpos PL/pgSQL delimitados con `$$ ... $$` pueden
contener `;` dentro sin romper el archivo.

Reglas del ejecutor:

- La tabla de control `schema_migrations` (versión, nombre, checksum, fecha)
  la crea y actualiza este módulo; por eso no aparece dentro de las
  migraciones numeradas.
- Cada archivo se aplica dentro de una transacción: PostgreSQL permite DDL
  transaccional, así que una migración fallida no deja cambios a medias. Si
  un archivo necesita ejecutar una sentencia no transaccional (por ejemplo
  `CREATE INDEX CONCURRENTLY`), su primera línea debe ser `-- NO-TRANSACCIONAL`
  y el ejecutor confirma cada sentencia por separado.
- Se rechaza aplicar si un archivo ya aplicado cambió el checksum: la
  corrección es una migración nueva, no editar el historial.
- **Base o "bootstrapping":** si un esquema ya se pobló con `db/schema.sql`
  por `psql`/pgAdmin y nunca se registró en `schema_migrations`, el ejecutor
  detecta las tablas de base, registra la migración `0001` como aplicada con
  su checksum real y no la vuelve a ejecutar. Así una base existente pasa al
  flujo versionado sin duplicar tablas ni datos.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import asyncpg

DIRECTORIO_MIGRACIONES = Path(__file__).resolve().parent / "migraciones"
SEPARADOR = "-- ---"
MARCA_NO_TRANSACCIONAL = "-- NO-TRANSACCIONAL"
PATRON_ARCHIVO = re.compile(r"^(?P<version>\d{4})_(?P<nombre>[a-z0-9_-]+)\.sql$")
SIGNO_EXISTENCIA_BASE = "estaciones"

SQL_TABLA_CONTROL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version       text PRIMARY KEY,
    nombre        text NOT NULL,
    checksum      text NOT NULL,
    aplicado_en   timestamptz NOT NULL DEFAULT now()
)
""".strip()


class ErrorMigracion(Exception):
    """Fallo al listar, aplicar o inspeccionar migraciones."""


@dataclass(frozen=True)
class ArchivoMigracion:
    """Un archivo `NNNN_descripcion.sql` con el checksum de su contenido."""

    version: str
    nombre: str
    ruta: Path
    checksum: str
    no_transaccional: bool


@dataclass(frozen=True)
class EstadoMigraciones:
    """Resultado de `migrar estado`: lo aplicado y lo pendiente."""

    aplicadas: tuple[tuple[str, str], ...]
    pendientes: tuple[tuple[str, str], ...]


def recalcular_checksum(texto: str) -> str:
    """Checksum SHA-256 del contenido exacto del archivo."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def listar_migraciones(directorio: Path = DIRECTORIO_MIGRACIONES) -> list[ArchivoMigracion]:
    """Lee y valida los archivos de migración, ordenados por versión."""
    if not directorio.is_dir():
        return []

    archivos: list[ArchivoMigracion] = []
    vistos: set[str] = set()

    for ruta in sorted(directorio.glob("*.sql")):
        hallazgo = PATRON_ARCHIVO.match(ruta.name)
        if hallazgo is None:
            raise ErrorMigracion(
                f"Nombre de migración inválido: '{ruta.name}'. "
                "Debe ser 'NNNN_descripcion.sql' (número de 4 dígitos y slug minúscula)."
            )
        version = hallazgo["version"]
        if version in vistos:
            raise ErrorMigracion(f"Dos archivos comparten la versión {version}.")
        vistos.add(version)

        texto = ruta.read_text(encoding="utf-8")
        no_transaccional = texto.lstrip().startswith(MARCA_NO_TRANSACCIONAL)
        archivos.append(
            ArchivoMigracion(
                version=version,
                nombre=hallazgo["nombre"],
                ruta=ruta,
                checksum=recalcular_checksum(texto),
                no_transaccional=no_transaccional,
            )
        )

    orden = {a.version: i for i, a in enumerate(archivos)}
    return sorted(archivos, key=lambda a: orden[a.version])


def dividir_sentencias(texto: str) -> list[str]:
    """Separa el SQL por la línea `-- ---` y descarta bloques vacíos."""
    segmentos: list[str] = []
    actual: list[str] = []
    for linea in texto.splitlines():
        if linea.strip() == SEPARADOR:
            segmentos.append("\n".join(actual))
            actual = []
        else:
            actual.append(linea)
    segmentos.append("\n".join(actual))

    sentencias = [segmento.strip() for segmento in segmentos if segmento.strip()]
    return [sentencia for sentencia in sentencias if _contiene_sql(sentencia)]


def _contiene_sql(sentencia: str) -> bool:
    """True si el segmento tiene al menos una línea con SQL y no solo comentarios."""
    return any(
        linea.strip() and not linea.strip().startswith("--")
        for linea in sentencia.splitlines()
    )


def listar_migraciones_texto(
    directorio: Path = DIRECTORIO_MIGRACIONES
) -> list[tuple[str, str]]:
    """Pares (versión, nombre) de los archivos existentes en orden."""
    return [(a.version, a.nombre) for a in listar_migraciones(directorio)]


def a_dsn(url: str) -> str:
    """Convierte `postgresql+asyncpg://user:pass@host/db` al DSN de asyncpg."""
    if not url:
        raise ErrorMigracion(
            "Falta MIGRADOR_URL en backend/.env: el ejecutor de migraciones "
            "conecta con el rol propietario `vales_migrador`, no con `vales_app`."
        )
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def aplicar(url: str, salida: Callable[[str], None] = print) -> list[str]:
    """Aplica todas las migraciones pendientes y devuelve las versiones nuevas."""
    archivos = listar_migraciones()
    connection = await asyncpg.connect(a_dsn(url))
    try:
        await connection.execute(SQL_TABLA_CONTROL)
        aplicadas = {
            fila["version"]: fila["checksum"]
            for fila in await connection.fetch(
                "SELECT version, checksum FROM schema_migrations ORDER BY version"
            )
        }

        for archivo in archivos:
            if archivo.version in aplicadas and aplicadas[archivo.version] != archivo.checksum:
                raise ErrorMigracion(
                    f"La migración {archivo.version} cambió después de aplicarse "
                    "(checksum distinto). Corregir es una migración nueva con "
                    "número mayor; nunca editar el historial."
                )

        huerfanas: set[str] = set(aplicadas) - {a.version for a in archivos}
        if huerfanas:
            salida(
                "⚠ Registradas en la base pero sin archivo en el repo: "
                + ", ".join(sorted(huerfanas))
            )

        # Línea base: un esquema poblado antes con db/schema.sql y sin registro
        # se adocta como `0001` ya aplicado, sin volver a ejecutarlo.
        primera = archivos[0] if archivos else None
        sql_base_poblada = (
            f"SELECT to_regclass('public.{SIGNO_EXISTENCIA_BASE}') IS NOT NULL"
        )
        base_poblada = bool(await connection.fetchval(sql_base_poblada))
        if (
            primera is not None
            and not aplicadas
            and base_poblada
            and primera.version == "0001"
        ):
            await connection.execute(
                "INSERT INTO schema_migrations (version, nombre, checksum) VALUES ($1, $2, $3)",
                primera.version,
                primera.nombre,
                primera.checksum,
            )
            salida(
                f"· {primera.version} ({primera.nombre}) registrada como aplicada: "
                "la base ya tenía el esquema de `backend/db/schema.sql`."
            )
            aplicadas[primera.version] = primera.checksum

        nuevas: list[str] = []
        for archivo in archivos:
            if archivo.version in aplicadas:
                continue
            sentencias = dividir_sentencias(archivo.ruta.read_text(encoding="utf-8"))
            if not sentencias:
                salida(f"⚠ {archivo.version} ({archivo.nombre}) no contiene sentencias; se omite.")
                continue

            try:
                posicion = 0
                if archivo.no_transaccional:
                    for sentencia in sentencias:
                        posicion += 1
                        await connection.execute(sentencia)
                else:
                    async with connection.transaction():
                        for sentencia in sentencias:
                            posicion += 1
                            await connection.execute(sentencia)
            except asyncpg.PostgresError as exc:
                total = len(sentencias)
                raise ErrorMigracion(
                    f"{archivo.version} ({archivo.nombre}) falló en la sentencia "
                    f"{posicion}/{total}: {exc}"
                ) from exc

            await connection.execute(
                "INSERT INTO schema_migrations (version, nombre, checksum) VALUES ($1, $2, $3)",
                archivo.version,
                archivo.nombre,
                archivo.checksum,
            )
            marca = " (no transaccional)" if archivo.no_transaccional else ""
            salida(
                f"✓ {archivo.version} ({archivo.nombre}): {len(sentencias)} sentencias{marca}."
            )
            nuevas.append(archivo.version)

        if not nuevas:
            salida("El esquema ya está al día: no hay migraciones pendientes.")
        return nuevas
    finally:
        await connection.close()


async def estado(url: str) -> EstadoMigraciones:
    """Devuelve lo registrado en `schema_migrations` y los archivos pendientes."""
    connection = await asyncpg.connect(a_dsn(url))
    try:
        await connection.execute(SQL_TABLA_CONTROL)
        filas = await connection.fetch(
            "SELECT version, nombre FROM schema_migrations ORDER BY version"
        )
        aplicadas = {f["version"] for f in filas}
        archivos = listar_migraciones()
        pendientes = [a for a in archivos if a.version not in aplicadas]
        return EstadoMigraciones(
            aplicadas=tuple((f["version"], f["nombre"]) for f in filas),
            pendientes=tuple((a.version, a.nombre) for a in pendientes),
        )
    finally:
        await connection.close()


def nueva(nombre: str, directorio: Path = DIRECTORIO_MIGRACIONES) -> Path:
    """Genera el siguiente archivo `NNNN_<slug>.sql` con la plantilla base."""
    slug = re.sub(r"[^a-z0-9]+", "_", nombre.strip().lower()).strip("_")
    if not slug:
        raise ErrorMigracion("El nombre de la migración debe formar un slug como 'agregar_tabla'.")

    existentes = listar_migraciones(directorio)
    siguiente = (max(int(a.version) for a in existentes) + 1) if existentes else 1
    version = f"{siguiente:04d}"
    plantilla = "\n".join(
        [
            f"-- Migración {version}: {slug}",
            "-- Describe el cambio de esquema y el motivo antes de aplicarla.",
            "-- Las sentencias se separan entre sí por una línea con «-- ---».",
            "-- Solo hacia adelante: corregir un error aquí exige una migración nueva.",
            "",
        ]
    )
    ruta = directorio / f"{version}_{slug}.sql"
    if ruta.exists():
        raise ErrorMigracion(f"Ya existe el archivo {ruta.name}.")
    if not directorio.is_dir():
        directorio.mkdir(parents=True)
    ruta.write_text(plantilla, encoding="utf-8")
    return ruta

"""Base de la batería de pruebas PostgreSQL (Fase 1).

Antes de importar `app.*` fija `DATABASE_URL` y `MIGRADOR_URL` sobre la base
de pruebas, para que el motor de la aplicación y las migraciones operen sobre
`vales_san_jose_test` (o la base que indiquen `DATABASE_URL_TEST` y
`MIGRADOR_URL_TEST`) y nunca sobre la base de desarrollo.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

RAIZ_BACKEND = Path(__file__).resolve().parents[1]

# Gama de tablas que se vacía entre pruebas. Se dejan fuera `schema_migrations`
# (control del ejecutor) y `parametros` (catálogo con los valores por defecto
# que instala la migración 0001).
TABLAS = (
    "impresiones_vale",
    "diferencias_integridad",
    "verificaciones_integridad",
    "auditoria",
    "movimientos_vale",
    "vales",
    "secuencias",
    "ocr_extracciones",
    "ordenes_compra",
    "instituciones",
    "precios_combustible",
    "combustibles",
    "tokens_recuperacion",
    "intentos_login",
    "refresh_tokens",
    "app_users",
    "estaciones",
)
TABLAS_INMUTABLES = ("movimientos_vale", "auditoria")


def _leer_env(ruta: Path) -> dict[str, str]:
    """Lee pares `CLAVE=VALOR` de un archivo .env simple, sin dependencias."""
    pares: dict[str, str] = {}
    if not ruta.is_file():
        return pares
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if not texto or texto.startswith(("#", ";")) or "=" not in texto:
            continue
        clave, _, valor = texto.partition("=")
        pares[clave.strip()] = valor.strip()
    return pares


def _config_env(clave: str) -> str:
    """Variables del entorno primero, después el archivo `.env`."""
    return os.environ.get(clave) or _leer_env(RAIZ_BACKEND / ".env").get(clave, "")


BASE_PRUEBAS = _config_env("DATABASE_URL_TEST")
MIGRADOR_PRUEBAS = _config_env("MIGRADOR_URL_TEST")

# La aplicación y las utilidades de migración apuntan a la base de pruebas
# durante toda la sesión de pytest.
os.environ["DATABASE_URL"] = BASE_PRUEBAS
os.environ["MIGRADOR_URL"] = MIGRADOR_PRUEBAS

# La batería debe ser determinista y sin servicios externos: el verificador
# de reCAPTCHA queda en modo local (rechaza solo los tokens de prueba
# declarados) y el correo de recuperación se imprime en consola (P-08).
os.environ["RECAPTCHA_SECRET_KEY"] = ""
os.environ["SMTP_HOST"] = ""

# Imports de la aplicación, después de fijar el entorno (pytest fixture setup).
# El noqa es intencional: ruff excluye E402 para conftest vía per-file-ignores.
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import migrar as migraciones

# pytest-asyncio 0.25 entrega un bucle por prueba; el pool del motor retiene
# conexiones atadas al bucle que las usó por primera vez y la siguiente
# prueba choca con 'Event loop is closed'. En pruebas, el motor usa NullPool
# (conexión nueva por uso) y la fábrica se rehace para que los endpoints la
# tomen del módulo reasignado.
from app.db import sesion as sesion_bd

motor_pruebas = create_async_engine(
    BASE_PRUEBAS,
    isolation_level="READ COMMITTED",
    poolclass=NullPool,
)
sesion_bd.motor = motor_pruebas
sesion_bd.FabricaSesiones = async_sessionmaker(motor_pruebas, expire_on_commit=False)

from app.main import app as aplicacion


@pytest.fixture(scope="session", autouse=True)
def esquema_migrado() -> None:
    """Aplica las migraciones pendientes a la base de pruebas, una sola vez."""
    if not BASE_PRUEBAS or not MIGRADOR_PRUEBAS:
        pytest.fail(
            "Configura DATABASE_URL_TEST y MIGRADOR_URL_TEST en backend/.env: "
            "las pruebas exigen una base propia (nunca la de desarrollo).",
            pytrace=False,
        )
    asyncio.run(migraciones.aplicar(MIGRADOR_PRUEBAS))


@pytest.fixture(autouse=True)
async def base_limpia() -> AsyncIterator[None]:
    """Vacía las tablas entre pruebas, punteando los disparadores inmutables."""
    connection = await asyncpg.connect(migraciones.a_dsn(MIGRADOR_PRUEBAS))
    try:
        for tabla in TABLAS_INMUTABLES:
            await connection.execute(f"ALTER TABLE {tabla} DISABLE TRIGGER USER")
        await connection.execute(
            "TRUNCATE " + ", ".join(TABLAS) + " RESTART IDENTITY CASCADE"
        )
        for tabla in TABLAS_INMUTABLES:
            await connection.execute(f"ALTER TABLE {tabla} ENABLE TRIGGER USER")
    finally:
        await connection.close()
    yield


@pytest.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    """Cliente HTTP sobre la aplicación ASGI con base en la base de pruebas."""
    transporte = ASGITransport(app=aplicacion)
    async with AsyncClient(transport=transporte, base_url="http://pruebas.local") as asgi:
        yield asgi

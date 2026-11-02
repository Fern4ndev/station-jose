"""Comprueba el entorno de desarrollo de la Fase 0.

Uso (desde `backend/`, con el entorno virtual activado):

    python scripts/verificar_entorno.py

Imprime una línea por comprobación y termina con código 0 solo si todas pasan.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MINIMO_PYTHON = (3, 11)
MINIMO_POSTGRES = 16

REQUISITO = re.compile(r"^(?P<nombre>[A-Za-z0-9._-]+)(?P<extra>\[[^\]]*\])?==(?P<version>.+)$")


class Comprobacion:
    """Resultado de una comprobación del entorno."""

    def __init__(self, nombre: str, correcto: bool, detalle: str) -> None:
        self.nombre = nombre
        self.correcto = correcto
        self.detalle = detalle


def leer_env(ruta: Path) -> dict[str, str]:
    """Lee un archivo .env sin depender de librerías adicionales."""
    valores: dict[str, str] = {}
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        clave, _, valor = limpia.partition("=")
        valores[clave.strip()] = valor.strip()
    return valores


def ejecutar(comando: list[str]) -> str | None:
    """Ejecuta un comando y devuelve su primera línea de salida."""
    try:
        salida = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    texto = (salida.stdout or salida.stderr or "").strip()
    return texto.splitlines()[0] if texto else None


def ubicar(herramienta: str) -> str | None:
    """Busca un ejecutable en el PATH y en las rutas habituales de fnm."""
    encontrado = shutil.which(herramienta)
    if encontrado:
        return encontrado

    raices = [
        Path(os.environ.get("APPDATA", "")) / "fnm" / "node-versions",
        Path(os.environ.get("LOCALAPPDATA", "")) / "fnm" / "node-versions",
        Path(os.environ.get("LOCALAPPDATA", "")) / "nvm",
    ]
    candidatos: list[Path] = []
    for raiz in raices:
        if raiz.is_dir():
            candidatos.extend(raiz.glob(f"*/installation/{herramienta}.exe"))
            candidatos.extend(raiz.glob(f"*/{herramienta}.exe"))
    if not candidatos:
        return None
    return str(sorted(candidatos)[-1])


def ubicar_pgadmin() -> str | None:
    """Busca pgAdmin 4 en el PATH y en sus carpetas de instalación habituales."""
    encontrado = shutil.which("pgadmin4")
    if encontrado:
        return encontrado

    programas = Path(os.environ.get("PROGRAMFILES", ""))
    bases = [
        programas / "pgAdmin 4",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "pgAdmin 4",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "pgAdmin 4",
    ]
    # PostgreSQL para Windows puede instalar pgAdmin junto al servidor.
    if (programas / "PostgreSQL").is_dir():
        bases.extend(sorted((programas / "PostgreSQL").glob("*/pgAdmin 4"), reverse=True))

    for base in bases:
        if not base.is_dir():
            continue
        for patron in ("runtime/pgAdmin4.exe", "*/runtime/pgAdmin4.exe"):
            for candidato in base.glob(patron):
                return str(candidato)
    return None


def dsn_asyncpg(url: str) -> str:
    """Convierte una URL de SQLAlchemy al formato que entiende asyncpg."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def consultar(url: str, sentencia: str) -> str:
    """Abre una conexión, ejecuta una sentencia escalar y la cierra."""
    import asyncpg

    conexion = await asyncpg.connect(dsn_asyncpg(url), timeout=10)
    try:
        return str(await conexion.fetchval(sentencia))
    finally:
        await conexion.close()


def dependencias_declaradas() -> list[tuple[str, str]]:
    """Devuelve (nombre, versión) de las dependencias de `pyproject.toml`."""
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    proyecto = datos["project"]
    declaradas = [*proyecto.get("dependencies", [])]
    declaradas.extend(proyecto.get("optional-dependencies", {}).get("dev", []))
    resultado: list[tuple[str, str]] = []
    for requisito in declaradas:
        coincidencia = REQUISITO.match(requisito)
        if coincidencia:
            resultado.append((coincidencia["nombre"], coincidencia["version"]))
    return resultado


def comprobar_python() -> Comprobacion:
    version = sys.version.split()[0]
    correcto = sys.version_info[:2] >= MINIMO_PYTHON
    minimo = f"{MINIMO_PYTHON[0]}.{MINIMO_PYTHON[1]}"
    return Comprobacion("Python", correcto, f"{version} (mínimo {minimo})")


def comprobar_venv() -> Comprobacion:
    activo = sys.prefix != sys.base_prefix
    detalle = sys.prefix if activo else "usa el intérprete global; active backend/.venv"
    return Comprobacion("Entorno virtual", activo, detalle)


def comprobar_dependencias() -> Comprobacion:
    declaradas = dependencias_declaradas()
    faltantes: list[str] = []
    for nombre, version in declaradas:
        try:
            instalada = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            faltantes.append(f"{nombre} (no instalada)")
            continue
        if instalada != version:
            faltantes.append(f"{nombre} {instalada} != {version}")
    correcto = not faltantes
    detalle = (
        f"{len(declaradas)} dependencias en su versión exacta" if correcto else "; ".join(faltantes)
    )
    return Comprobacion("Dependencias de pyproject.toml", correcto, detalle)


def comprobar_herramienta(nombre: str, comando: str) -> Comprobacion:
    ruta = ubicar(comando)
    if ruta is None:
        return Comprobacion(nombre, False, f"'{comando}' no está en el PATH")
    version = ejecutar([ruta, "--version"]) or "sin salida de versión"
    return Comprobacion(nombre, True, version)


def comprobar_rapidocr() -> Comprobacion:
    try:
        from rapidocr import RapidOCR

        motor = RapidOCR()
        version = importlib.metadata.version("rapidocr")
    except Exception as error:  # se informa cualquier fallo de carga
        return Comprobacion("RapidOCR", False, f"no se pudo cargar el modelo: {error}")
    del motor
    return Comprobacion("RapidOCR", True, f"{version} (modelo cargado)")


def comprobar_pgadmin() -> Comprobacion:
    ruta = ubicar_pgadmin()
    if ruta is None:
        return Comprobacion("pgAdmin 4", False, "no se encontró la aplicación")
    return Comprobacion("pgAdmin 4", True, ruta)


def comprobar_servidor(env: dict[str, str]) -> Comprobacion:
    url = env.get("MIGRADOR_URL", "")
    if not url:
        return Comprobacion("PostgreSQL", False, "falta MIGRADOR_URL en .env")
    try:
        version = asyncio.run(consultar(url, "SHOW server_version"))
    except Exception as error:  # se informa cualquier fallo de conexión
        return Comprobacion("PostgreSQL", False, f"sin conexión: {error}")
    mayor = int(version.split(".")[0])
    correcto = mayor >= MINIMO_POSTGRES
    return Comprobacion("PostgreSQL", correcto, f"{version} (mínimo {MINIMO_POSTGRES})")


def comprobar_base(env: dict[str, str], variable: str) -> Comprobacion:
    url = env.get(variable, "")
    if not url:
        return Comprobacion(variable, False, "no está definida en .env")
    try:
        identidad = asyncio.run(consultar(url, "SELECT current_user || '@' || current_database()"))
    except Exception as error:  # se informa cualquier fallo de conexión
        return Comprobacion(variable, False, f"sin conexión: {error}")
    return Comprobacion(variable, True, identidad)


def main() -> int:
    env = leer_env(RAIZ / ".env")

    comprobaciones = [
        comprobar_python(),
        comprobar_venv(),
        comprobar_dependencias(),
        comprobar_herramienta("Git", "git"),
        comprobar_herramienta("Node.js", "node"),
        comprobar_herramienta("psql", "psql"),
        comprobar_herramienta("pg_dump", "pg_dump"),
        comprobar_pgadmin(),
        comprobar_rapidocr(),
        comprobar_servidor(env),
        comprobar_base(env, "DATABASE_URL"),
        comprobar_base(env, "MIGRADOR_URL"),
        comprobar_base(env, "DATABASE_URL_TEST"),
        comprobar_base(env, "MIGRADOR_URL_TEST"),
    ]

    ancho = max(len(comprobacion.nombre) for comprobacion in comprobaciones)
    for comprobacion in comprobaciones:
        marca = "OK   " if comprobacion.correcto else "FALLA"
        print(f"[{marca}] {comprobacion.nombre.ljust(ancho)}  {comprobacion.detalle}")

    fallos = [comprobacion for comprobacion in comprobaciones if not comprobacion.correcto]
    print()
    if fallos:
        print(f"{len(fallos)} comprobación(es) fallida(s) de {len(comprobaciones)}.")
        return 1
    print(f"{len(comprobaciones)} comprobaciones correctas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

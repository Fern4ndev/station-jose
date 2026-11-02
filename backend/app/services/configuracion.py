"""Configuración del sistema (CFG-01, CFG-02).

Parámetros: cada uno se define en código con tipo, valor por defecto, rango
y descripción; el valor vigente vive en PostgreSQL (`parametros`) y el cambio
rija sin reiniciar porque los servicios lo leen en cada uso. La validación de
tipo y rango ocurre antes de guardar y cada cambio queda auditado.

Estación: una sola ficha en `estaciones` con nombre, RUC, dirección, teléfono
y correo; el logo se valida por contenido (PNG/JPG, 1 MB) y vive en
`almacenamiento/estacion/`.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import obtener_settings
from app.core import archivos, dinero
from app.errors import ErrorDominio
from app.services import auditoria

CODIGO_UNICO_VIOLADO = "23505"


@dataclass(frozen=True)
class DefinicionParametro:
    """Contrato de un parámetro: tipo, defecto, rango y texto de ayuda.

    `minimo` y `maximo` no aplican al tipo `texto`. `admite_vacio` marca los
    parámetros cuyo vacío significa "sin valor" (por ejemplo, vales sin
    vencimiento por defecto).
    """

    tipo: str  # "entero", "decimal" o "texto"
    defecto: str
    minimo: float
    maximo: float
    descripcion: str
    admite_vacio: bool = False


DEFINICIONES: dict[str, DefinicionParametro] = {
    "ocr_umbral_confianza": DefinicionParametro(
        "decimal", "0.80", 0.0, 1.0,
        "Score mínimo de la lectura OCR para considerarla confiable.",
    ),
    "archivo_max_mb": DefinicionParametro(
        "entero", "10", 1, 200,
        "Tamaño máximo de los documentos que se suben (en MB).",
    ),
    "vale_formato_numeracion_estacion": DefinicionParametro(
        "texto", "{anio}-{secuencia:06d}", 0, 0,
        "Formato de la numeración propia: debe incluir {anio} y {secuencia}.",
    ),
    "vale_vigencia_dias": DefinicionParametro(
        "entero", "", 1, 3650,
        "Vigencia por defecto de los vales en días; vacío sin vencimiento.",
        admite_vacio=True,
    ),
    "vale_umbral_saldo_bajo_pct": DefinicionParametro(
        "entero", "10", 1, 50,
        "Porcentaje de saldo a partir del cual un vale se marca como bajo.",
    ),
    "vale_dias_aviso_vencimiento": DefinicionParametro(
        "entero", "7", 1, 180,
        "Días antes del vencimiento en que se avisa al usuario.",
    ),
    "sesion_inactividad_min": DefinicionParametro(
        "entero", "60", 5, 1440,
        "Minutos de inactividad antes de que la sesión expire (AUT-08).",
    ),
    "login_intentos_max": DefinicionParametro(
        "entero", "5", 1, 20,
        "Intentos de login fallidos antes de bloquear el acceso.",
    ),
    "login_bloqueo_min": DefinicionParametro(
        "entero", "15", 1, 1440,
        "Minutos de bloqueo de acceso tras agotar los intentos.",
    ),
    "refresh_token_dias": DefinicionParametro(
        "entero", "30", 1, 90,
        "Días de vida del refresh token de la sesión.",
    ),
}

LOGO_MAX_BYTES = 1 * 1024 * 1024  # CFG-02: el logo pesa hasta 1 MB.


def _validar(valor: str, defi: DefinicionParametro, clave: str) -> str:
    """Aplica el tipo y el rango; 422 con el campo marcado si no cumple.

    Devuelve el valor normalizado: texto recortado, números como cadena.
    """
    texto = valor.strip()
    if defi.tipo == "texto":
        if "{anio}" not in texto or "{secuencia" not in texto:
            raise ErrorDominio(
                422,
                "VALIDACION_INVALIDA",
                "Revise los campos marcados.",
                {
                    clave: [
                        "El formato debe incluir {anio} y {secuencia}; por "
                        "ejemplo, '{anio}-{secuencia:06d}'."
                    ]
                },
            )
        return texto
    if texto == "" and defi.admite_vacio:
        return texto
    try:
        numero = dinero.a_decimal(texto)
    except dinero.ErrorNumero as exc:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {clave: [f"Debe ser un valor {'entero' if defi.tipo == 'entero' else 'decimal'}."]},
        ) from exc
    minimo = dinero.a_decimal(defi.minimo)
    maximo = dinero.a_decimal(defi.maximo)
    if numero < minimo or numero > maximo:
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {clave: [f"Debe estar entre {defi.minimo:g} y {defi.maximo:g}."]},
        )
    if defi.tipo == "entero" and numero != numero.to_integral_value():
        raise ErrorDominio(
            422,
            "VALIDACION_INVALIDA",
            "Revise los campos marcados.",
            {clave: ["Debe ser un número entero."]},
        )
    return texto


async def parametros_actuales(sesion: AsyncSession) -> list[dict]:
    """CFG-01: cada parámetro con su valor vigente y su contrato de validación."""
    guardados = (
        await sesion.execute(text("SELECT clave, valor FROM parametros"))
    ).mappings().all()
    valores = {str(fila["clave"]): str(fila["valor"]) for fila in guardados}
    return [
        {
            "clave": clave,
            "valor": valores.get(clave, definicion.defecto),
            "tipo": definicion.tipo,
            "defecto": definicion.defecto,
            "minimo": definicion.minimo,
            "maximo": definicion.maximo,
            "descripcion": definicion.descripcion,
        }
        for clave, definicion in DEFINICIONES.items()
    ]


async def guardar_parametros(
    sesion: AsyncSession,
    valores: dict[str, str],
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, str]:
    """CFG-01: valida y guarda un conjunto de parámetros; rige de inmediato.

    Devuelve el mapa completo clave → valor resultante de la base. El vacío
    de un parámetro que lo admite elimina su fila (queda el defecto del código).
    """
    for clave, valor in valores.items():
        defi = DEFINICIONES.get(clave)
        if defi is None:
            raise ErrorDominio(
                422,
                "VALIDACION_INVALIDA",
                "Revise los campos marcados.",
                {clave: ["No es un parámetro del sistema."]},
            )
        valor_validado = _validar(valor, defi, clave)
        if valor_validado == "":
            await sesion.execute(
                text("DELETE FROM parametros WHERE clave = :clave"), {"clave": clave}
            )
        else:
            await sesion.execute(
                text(
                    """
                    INSERT INTO parametros (clave, valor, actualizado_por)
                    VALUES (:clave, :valor, :actor)
                    ON CONFLICT (clave) DO UPDATE
                        SET valor = :valor, actualizado_por = :actor,
                            actualizado_en = now()
                    """
                ),
                {"clave": clave, "valor": valor_validado, "actor": actor_id},
            )
        await auditoria.registrar(
            sesion,
            usuario_id=actor_id,
            accion="actualizar_parametro",
            entidad="parametro",
            entidad_id=clave,
            despues={"valor": valor_validado},
            ip=ip,
            user_agent=user_agent,
        )
    guardados = (
        await sesion.execute(text("SELECT clave, valor FROM parametros"))
    ).mappings().all()
    return {str(fila["clave"]): str(fila["valor"]) for fila in guardados}


async def valor_texto(sesion: AsyncSession, clave: str) -> str | None:
    """Valor crudo del parámetro; None si nunca se guardó (usa el defecto quien llama)."""

    return (
        await sesion.execute(
            text("SELECT valor FROM parametros WHERE clave = :clave"), {"clave": clave}
        )
    ).scalar_one_or_none()


async def id_estacion_activa(sesion: AsyncSession) -> int | None:
    """Id de la ficha única de estación (una base de gestión, una sede activa)."""
    return await _id_estacion(sesion)


async def _id_estacion(sesion: AsyncSession) -> int | None:
    """Id de la ficha única de estación (solo dentro del módulo)."""
    return (
        await sesion.execute(
            text("SELECT id FROM estaciones WHERE activo = TRUE ORDER BY id LIMIT 1")
        )
    ).scalar_one_or_none()


async def obtener_estacion(sesion: AsyncSession) -> dict | None:
    """CFG-02: datos que se usan en comprobantes y vistas de impresión."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT nombre, ruc, direccion, telefono, correo, logo_path
                FROM estaciones
                WHERE activo = TRUE
                ORDER BY id
                LIMIT 1
                """
            )
        )
    ).mappings().first()
    if fila is None:
        return None
    return {
        "nombre": str(fila["nombre"]),
        "ruc": fila["ruc"],
        "direccion": fila["direccion"],
        "telefono": fila["telefono"],
        "correo": fila["correo"],
        "logo_path": fila["logo_path"],
    }


async def guardar_estacion(
    sesion: AsyncSession,
    *,
    nombre: str,
    ruc: str | None,
    direccion: str | None,
    telefono: str | None,
    correo: str | None,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """CFG-02: crea o actualiza la ficha única; devuelve el detalle nuevo."""
    id_actual = await _id_estacion(sesion)
    if id_actual is None:
        fila = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO estaciones (nombre, ruc, direccion, telefono, correo)
                    VALUES (:nombre, :ruc, :direccion, :telefono, :correo)
                    RETURNING nombre, ruc, direccion, telefono, correo, logo_path
                    """
                ),
                {
                    "nombre": nombre.strip(),
                    "ruc": ruc,
                    "direccion": direccion,
                    "telefono": telefono,
                    "correo": correo,
                },
            )
        ).mappings().one()
    else:
        await sesion.execute(
            text(
                """
                UPDATE estaciones
                SET nombre = :nombre, ruc = :ruc, direccion = :direccion,
                    telefono = :telefono, correo = :correo
                WHERE id = :id
                """
            ),
            {
                "id": id_actual,
                "nombre": nombre.strip(),
                "ruc": ruc,
                "direccion": direccion,
                "telefono": telefono,
                "correo": correo,
            },
        )
        fila = (
            await sesion.execute(
                text(
                    """
                    SELECT nombre, ruc, direccion, telefono, correo, logo_path
                    FROM estaciones
                    WHERE id = :id
                    """
                ),
                {"id": id_actual},
            )
        ).mappings().one()
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="actualizar_estacion",
        entidad="estacion",
        entidad_id=id_actual,
        despues={"nombre": str(fila["nombre"]), "ruc": fila["ruc"]},
        ip=ip,
        user_agent=user_agent,
    )
    return dict(fila)


def carpeta_logo() -> Path:
    """Carpeta del logo dentro del almacén privado del backend."""
    destino = Path(obtener_settings().almacenamiento_dir) / "estacion"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


async def subir_logo(
    sesion: AsyncSession,
    datos: bytes,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    """CFG-02: valida por contenido (PNG/JPG hasta 1 MB) y sustituye el logo.

    El path guardado es relativo a la carpeta de almacenamiento del backend.
    Devuelve el tipo MIME real del contenido validado.
    """
    archivo = archivos.validar(
        datos, uso="logotipo", formatos=("png", "jpg"), maximo_bytes=LOGO_MAX_BYTES
    )
    destino = carpeta_logo() / f"logo{archivo.extension}"
    # La E/S de disco va fuera del bucle de eventos; nunca bloquea la API.
    await asyncio.to_thread(destino.write_bytes, archivo.contenido)
    id_actual = await _id_estacion(sesion)
    if id_actual is None:
        id_actual = int(
            (
                await sesion.execute(
                    text(
                        """
                        INSERT INTO estaciones (nombre, logo_path)
                        VALUES (:nombre, :logo)
                        RETURNING id
                        """
                    ),
                    {"nombre": "Estación de servicio San José", "logo": destino.name},
                )
            ).scalar_one()
        )
    else:
        await sesion.execute(
            text("UPDATE estaciones SET logo_path = :logo WHERE id = :id"),
            {"logo": destino.name, "id": id_actual},
        )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="subir_logo",
        entidad="estacion",
        entidad_id=id_actual,
        despues={"logo_path": destino.name},
        ip=ip,
        user_agent=user_agent,
    )
    return {"media_type": archivo.media_type, "logo_path": destino.name}


async def leer_logo(sesion: AsyncSession) -> tuple[bytes, str] | None:
    """CFG-02: bytes del logo y su tipo MIME; None si nunca se subió."""
    fila = (
        await sesion.execute(
            text(
                """
                SELECT logo_path
                FROM estaciones
                WHERE logo_path IS NOT NULL
                ORDER BY id
                LIMIT 1
                """
            )
        )
    ).scalar_one_or_none()
    if not fila:
        return None
    ruta = carpeta_logo() / str(fila)
    try:
        datos = await asyncio.to_thread(ruta.read_bytes)
    except FileNotFoundError:
        return None
    formato = archivos.sniff_formato(datos)
    if formato is None:  # el archivo en disco dejó de ser un PNG/JPG válido
        return None
    media, _ = archivos.JPG if formato == "jpg" else archivos.PNG
    return datos, media

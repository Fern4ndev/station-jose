"""Casos de uso del módulo Instituciones (INS-01..09, plan sección 5.6).

Cada caso de uso es una función sobre la sesión; el router commitea. Las
instituciones nunca se borran físicamente (RN-11): la baja lógica es
`estado = 'inactiva'` y la reactivación la vuelve a `'activa'` conservando
todos sus datos, incluida la modalidad de numeración.

El RUC del DDL de `0001` es obligatorio (`varchar(11)`, CHECK de formato y
índice único). La verificación del dígito la hace [app.core.ruc][]
(INS-01) antes de tocar la base; la unicidad sale como `IntegrityError`
y aquí se traduce a la excepción que el router convierte en 409.
"""

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dinero, ruc
from app.errors import ErrorDominio
from app.services import auditoria

# Límite de paginación: se cota para que ninguna consulta traiga de más.
MAXIMA_POR_PAGINA = 100

CODIGO_UNICO_VIOLADO = "23505"

COLS_LISTA = (
    "id, nombre, ruc, tipo, modalidad_numeracion, estado, creado_en, actualizado_en"
)
COLS_FICHA = (
    "id, nombre, ruc, direccion, telefono, correo, representante, tipo,"
    " modalidad_numeracion, estado, creado_en, actualizado_en"
)


def _verificar_ruc(valor: str | None) -> None:
    """INS-01: presente y con dígito verificador cuadrado.

    El CHECK del DDL ya garantiza los 11 dígitos; aquí se valida el
    verificador para que el error llegue como 422 legible.
    """
    if not ruc.es_valido(valor):
        raise ErrorDominio(
            422,
            "RUC_INVALIDO",
            "El RUC de 11 dígitos no cuadra con su dígito verificador.",
            {"campo": "ruc"},
        )


async def buscar_por_id(sesion: AsyncSession, id_institucion: int) -> dict | None:
    """Fila completa de la institución o `None` si el id no existe."""
    filas = await sesion.execute(
        text(f"SELECT {COLS_FICHA} FROM instituciones WHERE id = :id"), {"id": id_institucion}  # noqa: S608
    )
    fila = filas.mappings().one_or_none()
    return dict(fila) if fila else None


async def verificar_ruc(sesion: AsyncSession, ruc_consultado: str) -> dict:
    """INS-01/OCR-08: validez del RUC y enlace a la institución existente.

    El endpoint de validación en vivo necesita saber tanto si el RUC pasa
    el dígito verificador como si ya está registrado; devuelve los dos
    datos en una sola consulta.
    """
    texto = ruc_consultado.strip()
    valido = ruc.es_valido(texto)
    existente = None
    if valido:
        filas = await sesion.execute(
            text(f"SELECT {COLS_LISTA} FROM instituciones WHERE ruc = :ruc"),  # noqa: S608
            {"ruc": texto},
        )
        fila = filas.mappings().one_or_none()
        if fila is not None:
            existente = dict(fila)
    return {"ruc": texto, "valido": valido, "institucion": existente}


async def listar(
    sesion: AsyncSession,
    *,
    texto: str | None = None,
    ruc_valor: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    pagina: int,
    por_pagina: int,
) -> tuple[list[dict], int]:
    """INS-03: listado paginado con texto, RUC exacto, tipo y estado."""
    por_pagina = min(max(por_pagina, 1), MAXIMA_POR_PAGINA)
    pagina = max(pagina, 1)
    condiciones: list[str] = []
    where_params: dict[str, object] = {}
    if texto:
        condiciones.append("(nombre ILIKE :patron OR ruc LIKE :patron)")
        where_params["patron"] = f"%{texto}%"
    if ruc_valor:
        condiciones.append("ruc = :ruc_exacto")
        where_params["ruc_exacto"] = ruc_valor
    if tipo:
        condiciones.append("tipo = :tipo")
        where_params["tipo"] = tipo
    if estado in ("activa", "inactiva"):
        condiciones.append("estado = :estado")
        where_params["estado"] = estado
    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas_total = await sesion.execute(
        text(f"SELECT count(*) FROM instituciones{where}"),  # noqa: S608
        where_params,
    )
    total = int(filas_total.scalar_one())
    filas = await sesion.execute(
        text(
            f"SELECT {COLS_LISTA} FROM instituciones{where}"  # noqa: S608
            " ORDER BY nombre, id"
            " LIMIT :limite OFFSET :desplazamiento"
        ),
        {**where_params, "limite": por_pagina, "desplazamiento": (pagina - 1) * por_pagina},
    )
    return [dict(fila) for fila in filas.mappings()], total


async def ficha(sesion: AsyncSession, id_institucion: int) -> dict:
    """INS-03/ficha: todos los campos + resumen de órdenes.

    Los agregados de vales, saldo y consumo del mes quedan en 0 hasta que
    la Fase 7 complete ese módulo, de modo que la ficha nunca se cae.
    """
    fila = await buscar_por_id(sesion, id_institucion)
    if fila is None:
        raise ErrorDominio(404, "INSTITUCION_NO_ENCONTRADA", "La institución no existe.")
    agregados = await sesion.execute(
        text(
            "SELECT count(*)::int AS ordenes,"
            " coalesce(sum(presupuesto_soles), 0)::numeric AS presupuesto_total"
            " FROM ordenes_compra WHERE institucion_id = :id"
        ),
        {"id": id_institucion},
    )
    suma = agregados.mappings().one()
    return {
        **fila,
        "ordenes": int(suma["ordenes"]),
        "presupuesto_total": dinero.como_texto(suma["presupuesto_total"] or 0),
        "vales_vigentes": 0,
        "saldo_vigente_soles": dinero.como_texto(0),
        "consumo_mes_soles": dinero.como_texto(0),
    }


CAMPOS_EDITABLES = (
    "nombre",
    "direccion",
    "telefono",
    "correo",
    "representante",
    "tipo",
    "modalidad_numeracion",
)
CAMPOS_SOLO_ADMIN_CON_ORDENES = ("ruc", "modalidad_numeracion")


async def crear(
    sesion: AsyncSession,
    *,
    nombre: str,
    ruc_valor: str,
    direccion: str | None,
    telefono: str | None,
    correo: str | None,
    representante: str | None,
    tipo: str,
    modalidad_numeracion: str,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> int:
    """INS-01: alta verificada. Devuelve el id de la institución creada.

    El cheque previo entrega el id de la institución con ese RUC (RF-INS-01:
    se informa y se enlaza a la existente); el índice único queda como
    respaldo de carrera y su `IntegrityError` mantiene el mismo código.
    """
    _verificar_ruc(ruc_valor)
    fila_previa = await sesion.execute(
        text("SELECT id FROM instituciones WHERE ruc = :ruc"), {"ruc": ruc_valor}
    )
    id_previo = fila_previa.scalar_one_or_none()
    if id_previo is not None:
        raise ErrorDominio(
            409,
            "RUC_DUPLICADO",
            "Ya existe otra institución con ese RUC.",
            detalles={"campo": "ruc", "institucion_id": int(id_previo)},
        )
    try:
        filas = await sesion.execute(
            text(
                """
                INSERT INTO instituciones (
                    nombre, ruc, direccion, telefono, correo,
                    representante, tipo, modalidad_numeracion
                ) VALUES (
                    :nombre, :ruc, :direccion, :telefono, :correo,
                    :representante, :tipo, :modalidad_numeracion
                )
                RETURNING id
                """
            ),
            {
                "nombre": nombre,
                "ruc": ruc_valor,
                "direccion": direccion,
                "telefono": telefono,
                "correo": correo,
                "representante": representante,
                "tipo": tipo,
                "modalidad_numeracion": modalidad_numeracion,
            },
        )
        id_nuevo = int(filas.scalar_one())
    except IntegrityError as error:
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "RUC_DUPLICADO",
                "Ya existe otra institución con ese RUC.",
                {"campo": "ruc"},
            ) from error
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="institucion_creada",
        entidad="instituciones",
        entidad_id=id_nuevo,
        antes=None,
        despues={"nombre": nombre, "ruc": ruc_valor},
        ip=ip,
        user_agent=user_agent,
    )
    return id_nuevo


async def editar(
    sesion: AsyncSession,
    id_institucion: int,
    *,
    datos: dict,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
    es_admin: bool,
) -> dict:
    """INS-04: edición parcial.

    El nombre, contacto, dirección y tipo los edita quien tenga el permiso;
    el RUC y la modalidad de numeración, solo un Administrador cuando la
    institución ya tiene órdenes registradas (plan INS-04).
    """
    anterior = await buscar_por_id(sesion, id_institucion)
    if anterior is None:
        raise ErrorDominio(404, "INSTITUCION_NO_ENCONTRADA", "La institución no existe.")
    fila_ordenes = await sesion.execute(
        text("SELECT count(*) FROM ordenes_compra WHERE institucion_id = :id"),
        {"id": id_institucion},
    )
    con_ordenes = int(fila_ordenes.scalar_one()) > 0
    interesa_ruc = datos.get("ruc", anterior["ruc"]) != anterior["ruc"]
    interesa_modalidad = (
        datos.get("modalidad_numeracion", anterior["modalidad_numeracion"])
        != anterior["modalidad_numeracion"]
    )
    if (interesa_ruc or interesa_modalidad) and con_ordenes and not es_admin:
        raise ErrorDominio(
            409,
            "SOLO_ADMINISTRADOR",
            "Con órdenes registradas, el RUC y la modalidad los cambia solo un Administrador.",
        )
    if interesa_ruc:
        _verificar_ruc(datos.get("ruc"))
        fila_previa = await sesion.execute(
            text("SELECT id FROM instituciones WHERE ruc = :ruc AND id <> :id"),
            {"ruc": datos.get("ruc"), "id": id_institucion},
        )
        id_previo = fila_previa.scalar_one_or_none()
        if id_previo is not None:
            raise ErrorDominio(
                409,
                "RUC_DUPLICADO",
                "Ya existe otra institución con ese RUC.",
                detalles={"campo": "ruc", "institucion_id": int(id_previo)},
            )
    conjuntos: list[str] = []
    params: dict[str, object] = {"id": id_institucion}
    for campo in (*CAMPOS_EDITABLES, "ruc"):
        if campo in datos and datos[campo] is not None:
            conjuntos.append(f"{campo} = :{campo}")
            params[campo] = datos[campo]
    if not conjuntos:
        return anterior
    conjuntos.append("actualizado_en = now()")
    try:
        filas = await sesion.execute(
            text(
                f"UPDATE instituciones SET {', '.join(conjuntos)}"  # noqa: S608
                " WHERE id = :id RETURNING *"
            ),
            params,
        )
        fila = dict(filas.mappings().one())
    except IntegrityError as error:
        if getattr(error.orig, "pgcode", None) == CODIGO_UNICO_VIOLADO:
            raise ErrorDominio(
                409,
                "RUC_DUPLICADO",
                "Ya existe otra institución con ese RUC.",
                {"campo": "ruc"},
            ) from error
        raise
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="institucion_editada",
        entidad="instituciones",
        entidad_id=id_institucion,
        antes=anterior,
        despues=fila,
        ip=ip,
        user_agent=user_agent,
    )
    return fila


async def desactivar(
    sesion: AsyncSession,
    id_institucion: int,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """INS-06: baja lógica (estado = 'inactiva'). La fila no se elimina."""
    anterior = await buscar_por_id(sesion, id_institucion)
    if anterior is None:
        raise ErrorDominio(404, "INSTITUCION_NO_ENCONTRADA", "La institución no existe.")
    await sesion.execute(
        text(
            "UPDATE instituciones SET estado = 'inactiva', actualizado_en = now()"
            " WHERE id = :id"
        ),
        {"id": id_institucion},
    )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="institucion_desactivada",
        entidad="instituciones",
        entidad_id=id_institucion,
        antes={"estado": anterior["estado"]},
        despues={"estado": "inactiva"},
        ip=ip,
        user_agent=user_agent,
    )


async def reactivar(
    sesion: AsyncSession,
    id_institucion: int,
    *,
    actor_id: int,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """INS-07: reactivación que conserva todos los datos de la fila."""
    anterior = await buscar_por_id(sesion, id_institucion)
    if anterior is None:
        raise ErrorDominio(404, "INSTITUCION_NO_ENCONTRADA", "La institución no existe.")
    if anterior["estado"] == "activa":
        raise ErrorDominio(
            409, "INSTITUCION_YA_ACTIVA", "La institución ya está activa."
        )
    await sesion.execute(
        text(
            "UPDATE instituciones SET estado = 'activa', actualizado_en = now()"
            " WHERE id = :id"
        ),
        {"id": id_institucion},
    )
    await auditoria.registrar(
        sesion,
        usuario_id=actor_id,
        accion="institucion_reactivada",
        entidad="instituciones",
        entidad_id=id_institucion,
        antes={"estado": "inactiva"},
        despues={"estado": "activa"},
        ip=ip,
        user_agent=user_agent,
    )

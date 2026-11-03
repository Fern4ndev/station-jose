"""Evaluacion del OCR contra la verdad terreno (Fase 10, plan seccion 6).

Une cada documento del `--grupo` elegido (desarrollo o prueba, de
`datos/division.json`) con su verdad terreno en `datos/verdad_terreno/`, corre
el pipeline real una vez por documento y mide: exactitud por campo, tasa de
campos no encontrados, tasa de campos incorrectos con confianza alta (al
menos el umbral), porcentaje de documentos completamente correctos y tiempo
medio, todo desglosado por categoria (digital, escaneo, foto).

El informe fechado queda en `informes/`; la consola imprime un resumen. El
grupo `prueba` se evalua UNA sola vez, al final, con el pipeline congelado
(VERSION_PIPELINE + etiqueta de git): no se ajusta nada después de verlo.

Uso:

    python scripts/evaluar_ocr.py --grupo desarrollo
    python scripts/evaluar_ocr.py --grupo desarrollo --umbral 0.75   # calibrar
    python scripts/evaluar_ocr.py --grupo prueba                     # final
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

RAIZ = Path(__file__).resolve().parents[1]

# Congelar antes de la evaluación final del grupo de prueba: apuntar este
# valor a la etiqueta de git del pipeline (`git tag ocr-v1 ...`) y no tocarlo
# más; todo informe deja constancia de la versión que la produjo.
VERSION_PIPELINE: Final[str] = "sin-congelar (desarrollo)"

DIVISION_POR_DEFECTO = RAIZ / "datos" / "division.json"
DOCUMENTOS_POR_DEFECTO = RAIZ / "datos" / "documentos"
VERDAD_POR_DEFECTO = RAIZ / "datos" / "verdad_terreno"
METAS_POR_DEFECTO = RAIZ / "datos" / "metas.json"
INFORMES_POR_DEFECTO = RAIZ / "informes"

CATEGORIAS: Final[dict[str, str]] = {
    "digital": "PDF con texto digital: se mide el camino de pdfplumber.",
    "escaneo": "PDF escaneado o imagen limpia: se mide el camino del OCR.",
    "foto": "Foto de camara (peor calidad): se mide el camino del OCR.",
}

VALORES = ("correcto", "incorrecto", "no_hallado")


def normalizar_para_comparar(valor: str) -> str:
    """Igualdad sin mayúsculas ni espacios dobles (las cajas del OCR varían)."""
    return " ".join(valor.casefold().split())


def comparar_documento(verdad: dict, campos: dict[str, tuple[str, float]], umbral: float) -> dict:
    """Compara una extracción con su verdad terreno y clasifica cada campo.

    `campos` trae (valor, confianza) por clave; un campo sin valor cuenta
    como `no_hallado` y, si su confianza llega al umbral pero el valor
    difiere, como `incorrecto` con confianza alta (el caso peor: el motor se
    atrevió y erró).
    """
    comparacion: dict[str, str] = {}
    diferencias: dict[str, dict] = {}
    for clave, esperado in verdad["campos"].items():
        leido, confianza = campos.get(clave, ("", 0.0))
        if not leido:
            resultado = "no_hallado"
        elif normalizar_para_comparar(leido) == normalizar_para_comparar(str(esperado)):
            resultado = "correcto"
        else:
            resultado = "incorrecto"
            diferencias[clave] = {
                "esperado": str(esperado),
                "leido": leido,
                "confianza": round(confianza, 4),
                "confianza_alta": confianza >= umbral,
            }
        comparacion[clave] = resultado
    return {
        "campos": comparacion,
        "diferencias": diferencias,
        "completo": all(v == "correcto" for v in comparacion.values()),
    }


def resumir(informes_doc: list[dict], metas: dict, umbral: float) -> dict:
    """Agrega los resultados por documento en las métricas de la Fase 10."""
    claves = sorted({clave for doc in informes_doc for clave in doc["campos"]})
    por_campo = {
        clave: {
            "correctos": 0,
            "incorrectos": 0,
            "no_hallados": 0,
            "incorrectos_confi_alta": 0,
            "leidos": 0,
        }
        for clave in claves
    }
    categorias = {nombre: _plantilla_categoria() for nombre in CATEGORIAS}
    global_ = _plantilla_categoria()

    for doc in informes_doc:
        categoria = doc["categoria"]
        for plantilla in (categorias[categoria], global_):
            plantilla["documentos"] += 1
            if doc["estado"] == "lista":
                plantilla["listos"] += 1
            else:
                plantilla["fallidos"] += 1
            plantilla["tiempo_ms"] += doc["tiempo_ms"]
        for clave, valor in doc["campos"].items():
            contador = por_campo[clave]
            contador["leidos"] += 1
            if valor == "correcto":
                contador["correctos"] += 1
            elif valor == "no_hallado":
                contador["no_hallados"] += 1
            else:
                contador["incorrectos"] += 1
                if doc["diferencias"].get(clave, {}).get("confianza_alta"):
                    contador["incorrectos_confi_alta"] += 1

    metas_campos = metas.get("campos", {})
    exactitud = {}
    for clave, contador in por_campo.items():
        leidos = contador["leidos"] or 1
        cruda = contador["correctos"] / leidos
        meta = metas_campos.get(clave)
        exactitud[clave] = {
            **contador,
            "exactitud": round(cruda, 4),
            "meta": meta,
            "cumple": cruda >= meta if meta is not None else None,
        }

    retorno = {
        "global": _cerrar(global_),
        "por_categoria": {
            nombre: _cerrar(plantilla)
            for nombre, plantilla in categorias.items()
            if plantilla["documentos"]
        },
        "exactitud_por_campo": exactitud,
        "umbral_usado": umbral,
    }
    total_completos = sum(1 for doc in informes_doc if doc["completo"])
    retorno["documentos_completos_pc"] = round(total_completos / (len(informes_doc) or 1) * 100, 2)
    return retorno


def _plantilla_categoria() -> dict:
    """Contadores nuevos por categoría (documentos, lista, fallida, tiempos)."""
    return {"documentos": 0, "listos": 0, "fallidos": 0, "tiempo_ms": 0}


def _cerrar(contador: dict) -> dict:
    """Tiempo medio y porcentaje de lecturas correctas de una categoría."""
    documentos = contador["documentos"] or 1
    salida = dict(contador)
    salida["tiempo_medio_ms"] = round(contador["tiempo_ms"] / documentos)
    salida["lecturas_listas_pc"] = round(contador["listos"] / documentos * 100, 2)
    return salida


def cargar_verdad(ruta: Path) -> dict:
    """Lee una verdad terreno y valida su forma mínima."""
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    faltan = ["archivo", "categoria", "campos"] - contenido.keys()
    if faltan:
        raise ValueError(f"{ruta.name}: faltan las claves {', '.join(sorted(faltan))}")
    if contenido["categoria"] not in CATEGORIAS:
        claves = ", ".join(sorted(CATEGORIAS))
        raise ValueError(f"{ruta.name}: categoria debe ser una de: {claves}")
    if contenido.get("borrador_generado_por_ocr") and not contenido.get(
        "revisada_dos_pasadas", False
    ):
        raise ValueError(
            f"{ruta.name}: es un borrador OCR sin doble revisión; "
            "no puede usarse como verdad terreno."
        )
    if contenido.get("estado_revision") == "pendiente_revision_usuario":
        raise ValueError(f"{ruta.name}: falta la revisión humana de verdad terreno.")
    return contenido


def cargar_division(ruta: Path, grupo: str) -> list[str]:
    """Devuelve la lista de archivos del grupo con validación amable."""
    division = json.loads(ruta.read_text(encoding="utf-8"))
    archivos = division.get(grupo, [])
    if not isinstance(archivos, list) or not archivos:
        print(
            f"El grupo '{grupo}' de {ruta.name} está vacío o no existe.",
            file=sys.stderr,
        )
        print(
            "Recolecta documentos con su verdad terreno y corre "
            "scripts/dividir_dataset.py primero.",
            file=sys.stderr,
        )
    return archivos


def correr(
    *,
    archivos: list[str],
    umbral: float,
    carpeta_documentos: Path,
    carpeta_verdad: Path,
    paso_desactivado: str | None = None,
) -> list[dict]:
    """Corre el pipeline por documento y compara con su verdad terreno."""
    from app.config import obtener_settings
    from app.services.ocr.pipeline import AjustesOcr, procesar
    from app.services.ocr.preprocesado import Pasos

    ajustes_app = obtener_settings()
    nombres_pasos = ("gris", "ruido", "inclinacion", "binarizacion", "escalado")
    pasos = Pasos(**{nombre: nombre != paso_desactivado for nombre in nombres_pasos})
    ajustes = AjustesOcr(
        dpi=ajustes_app.ocr_dpi,
        paginas_max=5,
        megapixeles_max=25.0,
        tiempo_segundos=ajustes_app.ocr_tiempo_segundos,
        turno_segundos=ajustes_app.ocr_turno_segundos,
        umbral_confianza=umbral,
        concurrencia=ajustes_app.ocr_concurrencia,
        pasos=pasos,
    )
    resultados: list[dict] = []
    for nombre in archivos:
        # Convención del README: `ORD-0123.pdf.json` para `ORD-0123.pdf`.
        verdad = cargar_verdad(carpeta_verdad / f"{Path(nombre).name}.json")
        ruta = carpeta_documentos / nombre
        if not ruta.is_file():
            raise FileNotFoundError(f"Falta el documento {nombre} en {carpeta_documentos}.")
        try:
            extraccion = procesar(ruta.read_bytes(), ajustes=ajustes)
            campos = {campo.clave: (campo.valor, campo.confianza) for campo in extraccion.campos}
        except Exception:  # la evaluación cuenta la falla; nunca imprime la traza
            claves = ("numero_orden", "fecha", "monto", "institucion")
            campos = dict.fromkeys(claves, ("", 0.0))
            extraccion = None
        resultado = comparar_documento(verdad, campos, umbral)
        resultados.append(
            {
                "archivo": nombre,
                "categoria": verdad["categoria"],
                "estado": "lista" if extraccion is not None else "fallida",
                "motivo": getattr(extraccion, "motivo", "LECTURA_ROTA"),
                "tiempo_ms": getattr(extraccion, "tiempo_ms", 0),
                "metodo": getattr(extraccion, "metodo", ""),
                **resultado,
            }
        )
        marca = "ok" if resultado["completo"] else "con diferencias"
        print(f"  {nombre}: {marca}")
        for clave, detalle in resultado["diferencias"].items():
            print(
                f"    {clave}: esperado '{detalle['esperado']}', leido "
                f"'{detalle['leido']}' ({detalle['confianza']:.2f})"
            )
    return resultados


def escribir_informe(
    *,
    grupo: str,
    resultados: list[dict],
    resumen: dict,
    umbral: float,
    carpeta_informes: Path,
    metas_usadas: bool,
    paso_desactivado: str | None,
) -> Path:
    """Guarda el informe fechado (JSON) en `informes/` y devuelve su ruta."""
    carpeta_informes.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(UTC)
    ruta = carpeta_informes / f"evaluacion_ocr_{grupo}_{ahora.strftime('%Y%m%d-%H%M%S')}.json"
    informe = {
        "version_pipeline": VERSION_PIPELINE,
        "grupo": grupo,
        "fecha_utc": ahora.isoformat(timespec="seconds"),
        "umbral_usado": umbral,
        "metas_definidas": metas_usadas,
        "paso_preprocesado_desactivado": paso_desactivado,
        "documentos": resultados,
        "resumen": resumen,
    }
    ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ruta


def correr_grupo(
    *,
    grupo: str,
    umbral: float,
    archivos: list[str],
    division: Path,
    documentos: Path,
    verdad: Path,
    metas_ruta: Path,
    informes: Path,
    paso_desactivado: str | None = None,
) -> dict:
    """Une división, documentos, verdad terreno e informe (lo que pide la Fase 10)."""
    if not division.is_file():
        raise SystemExit(f"No existe {division}: corre scripts/dividir_dataset.py.")
    if not archivos:
        raise SystemExit(f"El grupo '{grupo}' no tiene documentos en {division.name}.")
    metas: dict = {}
    if metas_ruta.is_file():
        metas = json.loads(metas_ruta.read_text(encoding="utf-8"))
        print(
            "Metas por campo (datos/metas.json):\n"
            + "\n".join(f"  {clave}: {valor}" for clave, valor in metas.get("campos", {}).items())
        )
    else:
        print("Sin metas por campo; corregir datos/metas.json antes de medir de verdad.")

    resultados = correr(
        archivos=archivos,
        umbral=umbral,
        carpeta_documentos=documentos,
        carpeta_verdad=verdad,
        paso_desactivado=paso_desactivado,
    )
    resumen = resumir(resultados, metas, umbral)

    def imprimir(titulo: str, bloque: dict) -> None:
        print(f"\n{titulo}")
        for clave, valor in bloque.items():
            print(f"  {clave}: {valor}")

    global_ = resumen["global"]
    print()
    imprimir(
        "Resumen del grupo " + grupo + " (" + str(global_["documentos"]) + " documentos)",
        {
            "lecturas listas": f"{global_['listos']} " f"({global_['lecturas_listas_pc']} %)",
            "fallidas": global_["fallidos"],
            "documentos completamente correctos": f"{resumen['documentos_completos_pc']} %",
            "tiempo medio": f"{global_['tiempo_medio_ms']} ms",
        },
    )
    print("\nExactitud por campo (umbral ", umbral, "):", sep="")
    for clave, datos in resumen["exactitud_por_campo"].items():
        estado = (
            "cumple"
            if datos["cumple"]
            else ("NO cumple" if datos["cumple"] is False else "sin meta")
        )
        print(
            f"  {clave}: {datos['exactitud']:.3f} ({estado}); "
            f"correctos {datos['correctos']}/{datos['leidos']}, "
            f"no hallados {datos['no_hallados']}, "
            f"incorrectos con confianza alta {datos['incorrectos_confi_alta']}"
        )
    imprimir(
        "Desglose por categoria definida:",
        {
            **CATEGORIAS,
            **{
                nombre: (
                    f"{plantilla['lecturas_listas_pc']} % listos, "
                    f"{plantilla['tiempo_medio_ms']} ms promedio"
                )
                for nombre, plantilla in resumen["por_categoria"].items()
            },
        },
    )

    ruta = escribir_informe(
        grupo=grupo,
        resultados=resultados,
        resumen=resumen,
        umbral=umbral,
        carpeta_informes=informes,
        metas_usadas=bool(metas),
        paso_desactivado=paso_desactivado,
    )
    print(f"\nInforme guardado en {ruta.relative_to(RAIZ)}")
    return resumen


def padre() -> argparse.ArgumentParser:
    """Argumentos del comando; compartido por la CLI y las pruebas de humo."""
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--grupo", choices=("desarrollo", "prueba"), required=True)
    argumentos.add_argument("--umbral", type=float, default=0.80)
    argumentos.add_argument(
        "--desactivar-paso",
        choices=("gris", "ruido", "inclinacion", "binarizacion", "escalado"),
        help="A/B en desarrollo: desactiva un paso de preprocesado.",
    )
    argumentos.add_argument("--division", type=Path, default=DIVISION_POR_DEFECTO)
    argumentos.add_argument("--documentos", type=Path, default=DOCUMENTOS_POR_DEFECTO)
    argumentos.add_argument("--verdad", type=Path, default=VERDAD_POR_DEFECTO)
    argumentos.add_argument("--metas", type=Path, default=METAS_POR_DEFECTO)
    argumentos.add_argument("--informes", type=Path, default=INFORMES_POR_DEFECTO)
    return argumentos


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del comando; devuelve el código de salida del proceso."""
    opciones = padre().parse_args(argv)
    archivos = cargar_division(opciones.division, opciones.grupo)
    correr_grupo(
        grupo=opciones.grupo,
        umbral=opciones.umbral,
        archivos=archivos,
        division=opciones.division,
        documentos=opciones.documentos,
        verdad=opciones.verdad,
        metas_ruta=opciones.metas,
        informes=opciones.informes,
        paso_desactivado=opciones.desactivar_paso,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

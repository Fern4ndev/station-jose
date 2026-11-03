# Dataset del OCR (Fase 10)

Esta carpeta concentra el material de medida del motor de lectura:

- `documentos/` — las órdenes reales anonimizadas (o autorizadas por escrito)
  en formatos variados: PDF digital, escaneo limpio y foto de cámara. Son
  datos sensibles: **fuera de git** (ignorado por `.gitignore`).
- `verdad_terreno/` — un JSON por documento con los valores revisados a mano,
  también fuera de git por la misma razón.
- `division.json` — la partición desarrollo/prueba generada con
  `scripts/dividir_dataset.py` (determinística por `--seed`).
- `metas.json` — la exactitud mínima exigida por campo, definida ANTES de
  medir (plan, sec. 6, Fase 10) y ajustada por el operador del proyecto.
- `../informes/` — los informes fechados de `scripts/evaluar_ocr.py` (JSON,
  agregados por campo y categoría, sin datos personales: aptos para git).

## Formato de la verdad terreno

Un archivo JSON por documento, con el **mismo nombre base** que el documento
(`ORD-0123.pdf.json` para `datos/documentos/ORD-0123.pdf`). Los valores van
en la forma normalizada que debe entregar el pipeline: fecha ISO
(`YYYY-MM-DD`), monto con punto decimal (`1500.00`), número de orden tal como
el extractor lo entrega (con o sin `-año`) e institución en una línea.

```json
{
  "archivo": "ORD-0123.pdf",
  "categoria": "digital",
  "campos": {
    "numero_orden": "0018-2026",
    "fecha": "2027-03-15",
    "monto": "1500.00",
    "institucion": "MUNICIPALIDAD DEMO DEL SUR S.A.C."
  },
  "datos_orden": {
    "numero_siaf": "...",
    "proveedor": {"razon_social": "...", "ruc": "..."},
    "sede": "Santa Marta o San José",
    "unidad_ejecutora": "...",
    "ruc_unidad_ejecutora": "...",
    "partidas": [
      {"cantidad": "...", "descripcion": "DIESEL S50", "precio_unitario": "...", "precio_total": "..."}
    ]
  },
  "notas": "sin datos reales; doble revisión pendiente",
  "revisada_dos_pasadas": false
}
```

Reglas de la recolección (plan, Fase 10):

1. De 30 a 50 órdenes reales, variando las tres categorías.
2. Cada verdad se revisa dos veces (por el mismo operador en una segunda
   pasada o por una segunda persona) antes de usarse; `revisada_dos_pasadas`
   deja constancia.
3. `categoria` debe ser `digital`, `escaneo` o `foto`.
4. Los originales se mantienen localmente en `datos/documentos/`, excluidos
   de Git. Antes de usarlos, revisar autorización de tratamiento y anonimizar
   datos personales ajenos a la orden.
5. El RUC de la unidad ejecutora se registra por separado del RUC del proveedor.
   La numeración de la orden se conserva tal como aparece y nunca se deduplica
   entre entidades distintas.
6. La cantidad, descripción, precio unitario y precio total se anotan por
   cada partida de combustible. No se completa un valor que no sea legible.

## Flujo del trabajo

```bash
# con los documentos y verdades en su lugar:
python scripts/dividir_dataset.py            # genera datos/division.json
python scripts/evaluar_ocr.py --grupo desarrollo   # medir y ajustar
python scripts/evaluar_ocr.py --grupo desarrollo --umbral 0.75  # calibrar
python scripts/evaluar_ocr.py --grupo prueba       # solo al final, 1 vez
```

- Ajustar una sola cosa por corrida (un paso de preprocesado o el umbral)
  y conservar los informes: cada uno guarda su `umbral_usado`.
- Antes de la evaluación `prueba`, congelar la versión del pipeline en
  `scripts/evaluar_ocr.py::VERSION_PIPELINE` apuntándola a la etiqueta de
  git (`ocr-v1`), y rehacer la división solo si la carpeta de documentos
  cambió desde la última.
- El grupo `prueba` no se usa para elegir ajustes: medirlo dos veces es
  medirle a tu propio conjunto.

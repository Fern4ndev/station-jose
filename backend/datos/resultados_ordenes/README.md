# Extracción de órdenes de compra

El archivo principal es `ordenes_extraidas.json`: contiene un registro por PDF
único, los campos extraídos y el texto OCR completo como evidencia. Los CSV
son vistas planas del mismo resultado:

- `resumen_ordenes.csv`: orden, Exp. SIAF, fecha, proveedor, RUC del proveedor,
  dirección, sede, unidad ejecutora y RUC de la unidad ejecutora.
- `partidas_combustible.csv`: código, descripción, cantidad, precio unitario,
  precio total y renglón de evidencia por combustible.

`null` significa que el campo no se pudo leer. Cada registro incluye
`advertencias`; las filas dudosas o aritméticamente inconsistentes se dejan en
`partidas_pendientes_revision`. La fecha solo se normaliza si forma una fecha
válida; una inversión del mes reconocida por patrón OCR queda señalada para
cotejo. `sede_estacion` se infiere del nombre legal del proveedor cuando dice
Santa Martha o San José. La etiqueta de entrega de las órdenes suele decir
“grifo del proveedor” sin detallar la sede exacta.

Estos son resultados OCR extraídos, no una verdad terreno certificada. La
evaluación de exactitud de la Fase 10 requiere cotejar los datos con cada PDF.
Los originales y resultados están excluidos de Git por contener órdenes
reales.

# Revisión de verdad terreno (Fase 10)

El CSV `revision_verdad_terreno.csv` contiene 30 órdenes, una por fila. Los
valores actuales son transcripciones OCR para cotejar y corregir contra el PDF
de la misma fila; todavía no se aceptan como verdad validada.

1. Revise número de orden, Exp. SIAF, fecha, proveedor/RUC, sede, unidad
   ejecutora/RUC y cada partida en `partidas_json` contra el PDF. El campo
   `monto_soles` debe coincidir con el total impreso en la orden.
2. Corrija las celdas donde el OCR se equivocó. En partidas, mantenga un JSON
   válido con cantidad, unidad, descripción, precio unitario y total.
3. Marque `revisada` como `si` solo después de haber cotejado la orden en dos
   pasadas. Agregue aclaraciones en `correcciones_usuario` si corrigió datos.
4. Guarde el CSV y ejecute desde `backend`:

   ```powershell
   .venv\Scripts\python.exe scripts\aplicar_revision_fase10.py
   ```

El importador actualiza los 30 JSON de `datos/verdad_terreno/`. Solo los
documentos marcados como revisados quedan habilitados para la evaluación.
Primero se calibra con los 21 documentos de desarrollo; los 9 de prueba se
reservan para una sola evaluación final.

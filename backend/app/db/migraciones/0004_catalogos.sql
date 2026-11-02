-- Migración 0004: catálogos de la Fase 4 (CFG-01/02, CMB-01..04).
-- Las tablas `estaciones`, `parametros`, `combustibles` y `precios_combustible`
-- ya existen desde la línea base `0001_base.sql`, con sus índices y
-- restricciones; esta migración solo cierra los permisos que la Fase 4 exige.
--
-- CMB-02/RN-16: el histórico de precios no se edita ni se elimina — un cambio
-- se registra como precio nuevo. El rol de la aplicación queda con
-- `SELECT, INSERT` únicamente sobre `precios_combustible`, en línea con lo que
-- el plan exige (y como ya sucede con `movimientos_vale` y `auditoria`).
-- La inalterabilidad de la *fila* la refuerza en la Fase 7 (`0007`) el patrón
-- de disparadores; los `GRANT` de `0001` concedían aquí el `UPDATE` de un
-- catálogo editable, decisión que esta fase corrige.
-- Solo hacia adelante: las sentencias se separan por una línea con «-- ---».

-- ---
REVOKE UPDATE, DELETE, TRUNCATE ON precios_combustible FROM vales_app;

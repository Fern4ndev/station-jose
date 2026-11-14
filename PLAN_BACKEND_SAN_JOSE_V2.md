# PLAN_BACKEND.md
# Plan de implementación del backend — Estación de Servicio San José

**Proyecto:** Sistema de control de órdenes de compra y vales de combustible  
**Entidad:** Estación de Servicio San José  
**Sedes:** San José y Santa Marta  
**Backend:** Python + FastAPI  
**Base de datos:** PostgreSQL  
**Versión del plan:** 2.1  
**Fuente funcional:** `REQUERIMIENTOS_FUNCIONALES_SAN_JOSE_V2.md`  
**Estado:** Plan técnico actualizado; no representa funcionalidades implementadas.

> **Actualización 2.1:** se adopta una arquitectura por capas organizada por responsabilidad, similar al árbol de referencia compartido (`app/core`, `app/routers`, `app/schemas`, `app/services`, `app/database.py` y `app/tables.py`). Se añade una capa de repositorios para aislar las consultas SQL y proteger las operaciones transaccionales del dominio.
>
> **Cambio funcional principal respecto a la versión anterior:** el vale no se registra anticipadamente por Oficina. Se crea junto con su primer despacho, realizado por el grifero. Un mismo vale puede tener múltiples atenciones parciales. Cada atención descuenta exclusivamente los galones realmente despachados del saldo del vale y del saldo de la línea de combustible de la orden. Oficina verifica posteriormente el registro contra el vale físico, sin volver a capturarlo.

---

# 1. Información general

## 1.1. Descripción

El backend administrará las órdenes de compra que las instituciones entregan a la Estación de Servicio San José, los vales físicos presentados por sus clientes y los despachos de combustible realizados por los griferos en las sedes San José y Santa Marta.

El personal de oficina registrará las órdenes de compra. Los griferos consultarán una orden y sus saldos antes de atender al cliente. Durante el primer despacho capturarán los datos del vale físico y registrarán la cantidad realmente entregada. Si el cliente no consume toda la cantidad autorizada, el mismo vale permanecerá con saldo y podrá utilizarse en atenciones posteriores.

El personal de oficina recibirá el vale físico después de la atención y verificará que la información capturada coincida con el documento. Esta verificación no generará un segundo vale ni modificará los galones despachados.

## 1.2. Problema que resuelve

Actualmente, las órdenes y los vales se controlan mediante Excel y registros manuales. Esto genera demoras, duplicidad de información y dificultad para conocer el saldo real de cada orden antes de despachar combustible.

El backend centralizará las operaciones y será la única fuente autorizada para calcular saldos, validar despachos y conservar la relación entre órdenes, vales, líneas de combustible, atenciones, usuarios y sedes.

## 1.3. Objetivo técnico

Construir una API REST segura, transaccional y mantenible que permita administrar usuarios, registrar órdenes, capturar vales en su primera atención, registrar despachos parciales, calcular saldos por tipo de combustible, compartir la información entre sedes, permitir la verificación administrativa y generar reportes/exportaciones. RapidOCR apoyará exclusivamente el registro de órdenes a partir de PDF.

## 1.4. Resultado esperado

Una API versionada y documentada, respaldada por PostgreSQL, con reglas de negocio centralizadas, saldos calculados desde los despachos persistidos, integridad referencial y control de concurrencia. El plan no declara que existan endpoints o servicios implementados; define lo que deberá construirse.

---

# 2. Objetivo y alcance

## 2.1. Alcance incluido

| Área | Alcance backend | RF |
|---|---|---|
| Usuarios | Crear usuarios, asignar uno de tres roles, habilitar/deshabilitar cuentas y cerrar sesión. | RF-001 a RF-005 |
| Supervisión de atenciones | Consultar atenciones realizadas por los griferos según permisos. | RF-006 |
| Órdenes | Registrar, consultar, buscar, filtrar, ordenar, paginar, modificar y eliminar únicamente cuando no existan vales asociados. | RF-007 a RF-012, RF-032 |
| Verificación administrativa | Listar atenciones pendientes y registrar la verificación del vale físico por Oficina. | RF-013 |
| Consulta operativa | Buscar órdenes por número o entidad; consultar vales anteriores y saldos antes de atender. | RF-014, RF-015 |
| Vales | Crear el vale durante la primera atención, consultar, paginar, ordenar, corregir datos descriptivos y bloquear su eliminación cuando tenga atenciones. | RF-015 a RF-018, RF-033 |
| Atenciones | Registrar múltiples despachos parciales para un mismo vale, identificando grifero, fecha, hora y sede. | RF-019 |
| Saldos | Calcular saldo de cada línea de orden y de cada línea de vale, validar límites y actualizar de forma atómica. | RF-020 a RF-024 |
| Sedes | Compartir órdenes y saldos entre San José y Santa Marta. Registrar la sede real de cada despacho. | RF-025 |
| Estados | Derivar automáticamente estados de disponibilidad y atención según los saldos. | RF-026 |
| Reportes | Reportes de órdenes y despachos por hora, día, semana y mes; filtros por fecha, usuario y estado; dashboard con gráficos. | RF-027 a RF-030 |
| Exportación | Exportar reportes a PDF y Excel. | RF-031 |
| OCR | Procesar exclusivamente PDF de órdenes mediante RapidOCR y devolver campos candidatos para completar el formulario. | RF-034 |

## 2.2. Fuera del alcance

No se implementarán en esta versión:

- Autorregistro de usuarios o acceso para clientes, proveedores y usuarios externos.
- Eliminación física de usuarios.
- Eliminación de vales que tengan atenciones registradas.
- Modificación o eliminación directa de atenciones confirmadas.
- Ajustes compensatorios de despachos erróneos hasta que el negocio apruebe el procedimiento correspondiente.
- Comparación de reportes entre períodos.
- Impresión directa de reportes o control de impresoras.
- Notificaciones o alertas proactivas. Los mensajes de bloqueo o validación sí forman parte de las respuestas normales de la API.
- Integraciones con correo, WhatsApp, facturación, pagos, mapas o sistemas gubernamentales.
- Importación o migración inicial de Excel/PDF.
- OCR de vales, fotografías o formatos diferentes de PDF de órdenes de compra.
- Almacenamiento permanente de PDF procesados mediante OCR.
- Operación offline, colas distribuidas, microservicios, Redis o Celery sin una necesidad aprobada.
- Reportes personalizados e indicadores de rendimiento.

Los registros históricos anteriores a la puesta en producción permanecerán en los archivos originales, fuera de la nueva base de datos. El historial consultable dentro del sistema será el generado desde su puesta en marcha, salvo que se apruebe posteriormente una migración.

## 2.3. Aspectos no funcionales relacionados

El sistema se utilizará desde computadoras de oficina y móviles de griferos, con acceso desde las dos sedes. No se adjuntó un documento RNF independiente; por eso los objetivos cuantitativos de disponibilidad, rendimiento, recuperación, retención, compatibilidad y seguridad deberán definirse en ese documento.

La API no ofrecerá operaciones offline. Si se interrumpe la conexión durante un despacho, el cliente deberá consultar el resultado usando la misma clave de idempotencia antes de reintentar. El backend garantizará que una solicitud repetida no duplique el despacho.

---

# 3. Documentación analizada

| Documento | Uso en este plan |
|---|---|
| `REQUERIMIENTOS_FUNCIONALES_SAN_JOSE_V2.md` | Fuente funcional vigente: 34 RF, 22 RN, tres actores, matriz de permisos y 20 puntos pendientes. |
| `PLAN_BACKEND_SAN_JOSE(1).md` | Plan anterior. Se conserva su organización y las decisiones todavía válidas; se corrigen las decisiones que contradicen la versión 2.0 de los RF. |
| `PLAN_BACKEND_FASTAPI.md` | Estructura técnica de referencia para arquitectura, datos, API, servicios, seguridad, pruebas, fases y trazabilidad. |
| Árbol `back-fareas/` compartido en la solicitud de actualización | Referencia de organización por capas: `app/core`, `app/routers`, `app/schemas`, `app/services`, archivos centrales de base de datos y entidades. Se adapta al dominio de órdenes, vales y atenciones; no se incorporan componentes ajenos como reconocimiento facial o firmware ESP32. |

No se adjuntó código fuente del backend, repositorio, esquema de base de datos desplegado ni contrato OpenAPI implementado. Por tanto, el diagnóstico es documental. Los endpoints de este plan son contratos propuestos, no endpoints existentes ni verificados.

---

# 4. Diagnóstico del proyecto

## 4.1. Estado actual

**Clasificación:** backend nuevo o pendiente de implementación verificable. No se proporcionó código fuente que permita afirmar que exista una implementación parcial.

## 4.2. Componentes por construir

1. Aplicación FastAPI, configuración y manejo global de errores.
2. PostgreSQL, SQLAlchemy 2.x y migraciones Alembic.
3. Catálogos de sedes y tipos de combustible.
4. Autenticación, sesiones y autorización por rol.
5. Usuarios y deshabilitación lógica.
6. Órdenes de compra con líneas por tipo de combustible.
7. Vales físicos con una o varias líneas autorizadas de combustible.
8. Atenciones como eventos independientes, con detalle por combustible.
9. Verificación de atenciones por Oficina.
10. Cálculo de saldos y estados derivados.
11. Reportes, dashboard y exportación PDF/XLSX.
12. Procesamiento temporal de PDF mediante RapidOCR.
13. Pruebas unitarias, de integración, API, concurrencia y seguridad.
14. Documentación OpenAPI, despliegue y procedimientos operativos.

## 4.3. Correcciones obligatorias respecto al plan anterior

| Plan anterior | Situación frente a RF V2 | Corrección en esta versión |
|---|---|---|
| Un vale solo puede tener una atención completa. | Contradice RF-019, RF-021 y RN-020. | Se admiten múltiples atenciones parciales por vale. |
| El vale se registra antes de la atención por un endpoint independiente. | Contradice RF-013, RF-014, RF-019 y RN-002. | El vale se crea junto con su primera atención en una sola transacción. |
| Una atención está relacionada 1:1 con un vale. | No permite registrar 10 autorizados, 5 despachados y luego otros 5. | Relación 1:N: un vale contiene varias atenciones. |
| La suma de galones autorizados de vales se resta/reserva del saldo de la orden. | Contradice RF-020: los galones de vales aún no despachados no son consumo. | El saldo de la orden descuenta exclusivamente galones realmente despachados. No se reserva saldo por autorización de vales. |
| OCR con Tesseract. | RF-034 especifica RapidOCR. | Se utiliza RapidOCR; PyMuPDF puede renderizar páginas PDF para OCR. |
| OCR genérico para PDF/imagen. | RF-034 limita la entrada a PDF de órdenes. | Solo PDF de órdenes de compra; no vales ni fotografías. |
| Reportes comparativos entre períodos. | RF V2 eliminó esa funcionalidad. | No crear endpoint, servicio ni consulta de comparación. |
| Impresión directa. | RF V2 eliminó esa funcionalidad. | No crear endpoint de impresión. La exportación PDF/XLSX sí permanece. |
| Oficina registra los vales. | Contradice el flujo operativo V2. | Oficina solo verifica los datos capturados por el grifero. |

## 4.4. Riesgos técnicos principales

| Riesgo | Impacto | Tratamiento |
|---|---|---|
| Dos griferos despachan simultáneamente contra una misma línea de orden. | Sobreconsumo. | Transacciones PostgreSQL, bloqueo de líneas y validación dentro de la transacción. |
| Reintento móvil después de una pérdida de conexión. | Doble despacho. | Clave de idempotencia única y consulta del resultado previo. |
| Número de vale repetido. | Vale duplicado o consumo mal asociado. | Identidad funcional por orden, emisor y número normalizado; restricción única. |
| Orden con diferentes combustibles. | Descuento cruzado entre combustibles. | Líneas independientes por combustible y referencias a la línea exacta. |
| Vale con varios combustibles. | Saldos mezclados. | Cabecera de vale y detalle de líneas de vale por combustible. |
| Cantidad autorizada confundida con consumo. | Saldo incorrecto de orden. | Separar galones autorizados de galones efectivamente despachados. |
| Vale parcialmente atendido y orden agotada. | Vale con saldo propio, pero sin saldo de orden para completar. | Mostrar saldo del vale y disponibilidad de su línea; bloquear el siguiente despacho si la orden no tiene saldo. |
| Corrección de despacho incorrecto no definida. | Alteración de saldos e historial. | No permitir editar/borrar el movimiento; bloquear el ajuste hasta aprobar PD-006. |
| Oficina observa diferencias en el vale físico. | Registros no conciliados. | Estado de verificación `OBSERVED`; no modificar el despacho automáticamente. |
| OCR inexacto. | Datos erróneos en la orden. | Resultado OCR preliminar, revisión humana obligatoria y captura manual alternativa. |

---

# 5. Requerimientos identificados

## 5.1. Actores

| Actor | Rol técnico | Responsabilidad backend |
|---|---|---|
| Administrador | `ADMIN` | Acceso a todos los módulos, administración de usuarios, supervisión, consulta de atenciones, corrección de datos descriptivos de vales y reportes. |
| Personal de oficina | `OFFICE` | Registro y mantenimiento de órdenes, revisión de atenciones/vales físicos, consulta y exportación de reportes. No registra el despacho de combustible. |
| Grifero | `ATTENDANT` | Consulta órdenes y saldos, captura un vale en la primera atención y registra únicamente los despachos que realiza. |

La cantidad estimada de usuarios es ocho, aunque el levantamiento también menciona seis trabajadores. El backend no impondrá un límite fijo de cuentas.

## 5.2. Módulos y requerimientos

| ID | Módulo | RF |
|---|---|---|
| MOD-001 | Administración de usuarios y acceso | RF-001 a RF-006 |
| MOD-002 | Gestión de órdenes de compra | RF-007 a RF-012, RF-032 |
| MOD-003 | Atención de vales y verificación administrativa | RF-013 a RF-019, RF-033 |
| MOD-004 | Control de saldos y estados | RF-020 a RF-026 |
| MOD-005 | Reportes y panel principal | RF-027 a RF-031 |
| MOD-006 | OCR para órdenes de compra | RF-034 |

## 5.3. Reglas de negocio que debe proteger el backend

- **RN-001:** La orden de compra debe existir antes de atender un vale.
- **RN-002:** El vale se crea en la misma operación que su primera atención.
- **RN-003:** La orden contiene número, expediente SIAF, fecha, proveedor, unidad ejecutora, RUC y una o más líneas de combustible.
- **RN-004:** El primer despacho captura número de vale, entidad emisora, orden, combustible y galones autorizados.
- **RN-005:** El despacho no puede superar el saldo disponible de la línea de orden correspondiente.
- **RN-006:** La orden se descuenta solo por consumo real.
- **RN-007:** Saldo del vale = galones autorizados menos suma de galones realmente despachados en sus atenciones.
- **RN-008:** Los saldos se calculan automáticamente; no se editan manualmente.
- **RN-009:** Los estados de consumo son automáticos y no se modifican manualmente.
- **RN-010:** Los permisos son predefinidos por rol y validados en backend.
- **RN-011:** El grifero no registra órdenes ni verifica vales; solo consulta y despacha.
- **RN-012:** Cada despacho registra usuario, fecha/hora del servidor y sede.
- **RN-013:** Las dos sedes consultan una fuente centralizada.
- **RN-014:** Los vales atendidos y despachos no se eliminan; los usuarios se deshabilitan.
- **RN-015:** Las operaciones administrativas permitidas requieren confirmación en la interfaz; el backend valida además las reglas de negocio.
- **RN-016:** Una orden solo se elimina si no tiene vales asociados.
- **RN-017:** Un despacho confirmado no se edita ni elimina directamente.
- **RN-018:** La identidad del vale considera como mínimo entidad emisora, número y orden.
- **RN-019:** Oficina verifica posteriormente el documento físico; verificar no genera otro vale ni modifica cantidades.
- **RN-020:** Un vale puede tener varias atenciones parciales.
- **RN-021:** RapidOCR procesa únicamente PDF de órdenes; la revisión humana precede al registro.
- **RN-022:** No se pueden reducir cantidades o eliminar líneas de orden por debajo de consumos ya registrados ni romper relaciones históricas.

## 5.4. Prioridad funcional

El camino crítico es: registrar orden → localizar orden → crear/capturar vale en primer despacho → registrar atenciones parciales → calcular saldos → consultar saldos → verificar físicamente → reportar. Autenticación y permisos son prerrequisitos de seguridad aunque el levantamiento los clasifique como prioridad media/alta.

---

# 6. Decisiones arquitectónicas

## 6.1. ADR — Decisiones propuestas

| ID | Decisión | Justificación |
|---|---|---|
| ADR-001 | Monolito modular con FastAPI. | El alcance no justifica microservicios ni despliegues distribuidos. |
| ADR-002 | PostgreSQL como única base de producción. | Integridad relacional, transacciones, restricciones, bloqueos y consultas de reportes. |
| ADR-003 | SQLAlchemy 2.x síncrono. | Simplicidad operativa; la consistencia se logra con transacciones y locks, no por usar async. |
| ADR-004 | Separar cabecera de orden, líneas de combustible, vale, líneas de vale, atención y detalle de atención. | Permite múltiples combustibles y múltiples despachos parciales sin mezclar saldos. |
| ADR-005 | El vale nace con su primera atención. | Cumple RN-002 y evita un registro administrativo duplicado. |
| ADR-006 | Un vale admite N atenciones y una atención puede contener N líneas de combustible. | Permite despachos parciales y documentos con diferentes tipos de combustible. |
| ADR-007 | El saldo de orden se descuenta solo por galones despachados. | Es la fórmula explícita de RF-020; la autorización del vale no es consumo. |
| ADR-008 | Los saldos no se persisten como contadores editables. | Se calculan a partir de autorizaciones y detalles de atenciones. |
| ADR-009 | Uso de transacciones y bloqueos por línea de orden. | Impide que dos sedes consuman simultáneamente más saldo del disponible. |
| ADR-010 | Atenciones confirmadas inmutables. | RN-017; un error requiere procedimiento de ajuste pendiente de aprobación. |
| ADR-011 | Verificación administrativa separada del consumo. | La verificación del vale físico no debe modificar cantidades ni saldos. |
| ADR-012 | Estados derivados de saldos; verificación como estado independiente. | Evita confundir disponibilidad del combustible con revisión administrativa. |
| ADR-013 | Deshabilitación lógica de usuarios. | Conserva identidad de las operaciones históricas. |
| ADR-014 | Borrado lógico de órdenes solo si no tienen vales. | Cumple RF-012 y preserva referencias. |
| ADR-015 | Sin eliminación de vales atendidos. | Todo vale operativo nace con al menos una atención. |
| ADR-016 | Roles fijos `ADMIN`, `OFFICE`, `ATTENDANT`. | El RF define tres perfiles preestablecidos y no permisos personalizados. |
| ADR-017 | Fuente de datos compartida por las dos sedes. | Cumple RF-025. |
| ADR-018 | Sede del despacho tomada del usuario autenticado. | Evita que el cliente manipule la procedencia de una atención. |
| ADR-019 | RapidOCR sobre páginas PDF renderizadas. | Cumple RF-034 y no introduce servicios OCR externos. |
| ADR-020 | Sin Redis, Celery ni cola de trabajos en primera versión. | El OCR y los reportes no justifican una infraestructura distribuida en el alcance actual. |
| ADR-021 | API versionada `/api/v1`. | Mantiene contrato explícito para el frontend Angular. |
| ADR-022 | Fechas almacenadas en UTC y presentación/agrupación en `America/Lima`. | Evita ambigüedad de hora; la zona final se valida como PD-019. |

## 6.2. Modelo correcto de cantidades y saldos

Se debe separar claramente cada concepto:

- **Galones autorizados de la línea de orden:** cantidad máxima de combustible de ese tipo en la orden.
- **Galones autorizados de la línea del vale:** cantidad indicada en el documento físico para ese tipo de combustible.
- **Galones despachados:** cantidad que realmente se entregó en una atención específica.
- **Galones acumulados del vale:** suma de todos los detalles de atención asociados a la línea del vale.
- **Saldo del vale:** autorizados del vale menos galones acumulados del vale.
- **Galones acumulados de la orden:** suma de todos los despachos reales de todos los vales que consumen esa línea de orden.
- **Saldo de la orden:** galones autorizados de la línea de orden menos despachos reales acumulados de esa línea.

**Regla crítica:** los galones autorizados de vales que aún no han sido despachados NO se descuentan del saldo de la orden. Tampoco se debe sumar o restar autorización de vales para simular consumo. Una orden puede tener varios vales pendientes cuyas autorizaciones acumuladas excedan el saldo remanente; cada nuevo despacho se validará contra el saldo real de la orden y el saldo del vale.

Ejemplo de cálculo:

| Concepto | Galones |
|---|---:|
| Orden de Diesel autorizada | 100 |
| Vale A autorizado | 10 |
| Vale A despachado en primera atención | 5 |
| Saldo del Vale A | 5 |
| Saldo de la orden | 95 |
| Vale B autorizado y todavía no atendido | 20 |
| Saldo de la orden después de registrar solo la autorización del Vale B | 95 |

La autorización de 20 galones del Vale B no consume la orden. Si más adelante se despachan 7 galones del Vale B, el saldo de la orden será 88 y el saldo del Vale B será 13.

## 6.3. Modelo de vale con varios combustibles

La estructura debe admitir que un documento físico contenga una o varias cantidades autorizadas por tipo de combustible. Se utilizará:

- Una cabecera `vouchers` para identificar el documento físico (emisor, número y orden).
- Una o varias líneas `voucher_items`, cada una relacionada con una línea específica de la orden y con sus galones autorizados.
- Una o varias cabeceras `attendances`, una por evento/visita de despacho.
- Una o varias líneas `attendance_items` por atención, que guardan los galones despachados de cada línea del vale.

Así se pueden atender parcialmente uno o varios combustibles y no se mezclan, por ejemplo, galones de Diesel con galones de gasolina.

## 6.4. Estados derivados

Los estados de consumo no se editan desde endpoints administrativos. Se calculan a partir de los saldos.

### Estado de línea de orden

| Estado | Condición |
|---|---|
| `AVAILABLE` | Saldo de la línea mayor que cero. |
| `DEPLETED` | Saldo de la línea igual a cero. |

### Estado de vale por línea

| Estado | Condición |
|---|---|
| `PENDING` | No tiene galones despachados y su saldo propio es mayor que cero. |
| `PARTIALLY_ATTENDED` | Tiene galones despachados y saldo propio mayor que cero. |
| `COMPLETED` | Su saldo propio es cero. |
| `BLOCKED_BY_ORDER_BALANCE` | Conserva saldo propio, pero la línea de la orden ya no tiene saldo para continuar. |

El estado agregado de un vale se calculará a partir de sus líneas. Si contiene varias líneas, la respuesta deberá incluir el estado individual de cada una y un estado general (`PENDING`, `PARTIALLY_ATTENDED`, `COMPLETED` o `PARTIALLY_BLOCKED`). El estado `BLOCKED_BY_ORDER_BALANCE` no significa que el vale se haya consumido; significa que el saldo autorizado del vale no puede continuar atendiéndose porque la orden se agotó.

### Estado de orden

- `AVAILABLE`: al menos una línea de combustible conserva saldo.
- `DEPLETED`: todas las líneas de combustible tienen saldo cero.

### Estado de verificación

La revisión del vale físico se manejará de forma independiente del estado de consumo:

- `PENDING`: una atención todavía no ha sido revisada por Oficina.
- `VERIFIED`: Oficina confirmó que la información coincide con el documento físico.
- `OBSERVED`: Oficina encontró diferencias y registró una observación.

Una verificación no modifica saldos. Una atención con estado `OBSERVED` no se corrige editando la cantidad real despachada; el procedimiento de ajuste de cantidades está pendiente de aprobación.

## 6.5. Política de captura y despacho

### Primera atención de un vale

1. El grifero localiza una orden existente.
2. Consulta saldo disponible por línea de combustible.
3. Captura emisor, número del vale y líneas autorizadas por tipo de combustible.
4. Ingresa el despacho real de la visita para una o varias líneas.
5. El backend crea cabecera de vale, líneas del vale, atención y detalles de atención en una única transacción.
6. Si cualquier validación o escritura falla, no se guarda ninguna parte.

### Atenciones posteriores

1. El grifero localiza el mismo vale.
2. El backend muestra sus galones autorizados, acumulados y restantes por línea.
3. El grifero ingresa la cantidad real que entregará en esa visita.
4. El backend valida saldos de vale y orden, registra una nueva atención y recalcula las disponibilidades.

El backend no permitirá crear otro vale con la misma identidad funcional. Para un vale institucional, la identidad mínima será orden + emisor + número normalizado. Para un vale emitido por la estación, se mantendrá un correlativo central y único.

---

# 7. Stack tecnológico

## 7.1. Tecnologías

| Componente | Tecnología | Uso |
|---|---|---|
| Lenguaje | Python 3.12 o versión estable compatible con dependencias | Backend. |
| Framework | FastAPI | API REST y OpenAPI. |
| ASGI | Uvicorn | Servidor. |
| Validación | Pydantic v2 | Requests, responses y configuración. |
| Configuración | `pydantic-settings` | Variables de entorno. |
| ORM | SQLAlchemy 2.x | Persistencia relacional. |
| Driver | Psycopg 3 | Conexión PostgreSQL. |
| Migraciones | Alembic | Versionado del esquema. |
| JWT | PyJWT | Firma y validación de tokens. |
| Password hashing | `pwdlib` + Argon2 | Hash seguro de contraseñas. |
| Pruebas | Pytest + HTTPX | Unitarias, integración y API. |
| Calidad | Ruff + Mypy | Formato, lint y tipos. |
| Excel | openpyxl | Exportación XLSX. |
| PDF | ReportLab | Exportación PDF. |
| OCR | RapidOCR | Reconocimiento de texto de órdenes. |
| PDF rendering | PyMuPDF | Renderizar páginas del PDF para RapidOCR. |
| Upload | `python-multipart` | Recepción `multipart/form-data` del PDF. |
| Contenedores | Docker + Compose | Desarrollo y despliegue reproducible. |

Las versiones exactas se fijarán en `requirements.txt` y `requirements-dev.txt` después de comprobar compatibilidad. `pyproject.toml` conservará la configuración del proyecto y de las herramientas. No se utilizarán dependencias flotantes en producción.

## 7.2. Base de datos

PostgreSQL será el único motor de producción. Es apropiado para las relaciones del dominio, restricciones únicas, precisión decimal, transacciones ACID, `SELECT FOR UPDATE` y consultas agregadas.

Las pruebas de concurrencia y transacciones deben ejecutarse contra PostgreSQL real, no depender únicamente de SQLite.

## 7.3. Dependencias principales

Dependencias base previstas:

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `pydantic-settings`
- `sqlalchemy`
- `psycopg`
- `alembic`
- `pyjwt`
- `pwdlib[argon2]`
- `email-validator`
- `python-multipart`
- `pytest`
- `httpx`
- `ruff`
- `mypy`
- `openpyxl`
- `reportlab`

## 7.4. Dependencias OCR

- RapidOCR, mediante el paquete Python compatible con el runtime elegido.
- PyMuPDF para abrir PDF, verificar páginas y renderizar imágenes de página.
- Runtime de inferencia requerido por la distribución de RapidOCR elegida (por ejemplo ONNX Runtime), fijado y probado junto con las demás dependencias.

No se instalará Tesseract como motor alternativo en esta versión, para evitar dos motores OCR con resultados distintos. Si RapidOCR no reconoce un campo, el usuario lo completará manualmente.

---

# 8. Arquitectura del backend

## 8.1. Estilo arquitectónico

Se utilizará un **monolito modular con arquitectura por capas organizada por responsabilidad** (*layered architecture*). La estructura de carpetas seguirá el estilo de referencia compartido: directorios principales para `core`, `routers`, `schemas`, `services` y persistencia; archivos centrales `database.py` y `tables.py`.

Esta organización también aplicará principios de Clean Code y separación de responsabilidades, pero no se presentará como Clean Architecture estricta ni como Domain-Driven Design. El proyecto no necesita microservicios ni una estructura compleja de agregados para su alcance actual.

La capa `repositories/` se incorpora como adaptación específica del sistema San José: los saldos por combustible, las consultas agregadas, los bloqueos `SELECT FOR UPDATE` y la idempotencia requieren aislar el acceso a PostgreSQL de los casos de uso. Esta carpeta amplía el árbol de referencia sin cambiar su estilo general.

## 8.2. Capas y responsabilidades

| Capa / ubicación | Responsabilidad | No debe hacer |
|---|---|---|
| `routers/` | Recibir HTTP, declarar rutas, parámetros, dependencias, códigos de estado y respuestas. Invocar servicios. | Ejecutar SQL, calcular saldos, abrir transacciones de negocio o implementar reglas. |
| `schemas/` | Definir contratos Pydantic de entrada, salida, filtros y paginación. Validar forma y tipos de los datos. | Consultar la base de datos o convertirse en la fuente de reglas de negocio. |
| `services/` | Implementar casos de uso y reglas del dominio; coordinar repositorios, permisos contextuales y transacciones. | Contener detalles HTTP ni duplicar consultas SQL complejas. |
| `repositories/` | Encapsular consultas y operaciones de persistencia SQLAlchemy, filtros, joins, agregaciones y bloqueos. | Decidir permisos HTTP, construir respuestas FastAPI o ejecutar `commit` por su cuenta. |
| `tables.py` | Declarar `Base`, entidades SQLAlchemy, relaciones, restricciones e índices. | Contener casos de uso, endpoints o serialización de API. |
| `database.py` | Crear engine, `SessionLocal` y dependencia de sesión; administrar conexión y ciclo de vida de sesiones. | Contener operaciones de negocio o consultas específicas de módulos. |
| `core/` | Configuración, autenticación, autorización, excepciones, logging, paginación y utilidades transversales. | Acumular lógica exclusiva de órdenes, vales o reportes. |
| `ai/` | Encapsular el motor técnico RapidOCR y el procesamiento de páginas/documentos. | Guardar órdenes, decidir permisos o cambiar saldos. |

### Reglas de dependencia

1. Un router puede utilizar schemas, dependencias de `core/` y servicios.
2. Un servicio coordina uno o varios repositorios y puede utilizar políticas/utilidades de `core/`.
3. Un repositorio utiliza la sesión de base de datos y las entidades declaradas en `tables.py`.
4. `schemas/` no importa routers, servicios ni repositorios.
5. `tables.py` no importa servicios, routers ni schemas de API.
6. `core/` no importa módulos de negocio para evitar dependencias circulares.
7. El motor OCR se invoca desde `PurchaseOrderOcrService`; el router OCR no debe llamar directamente al motor.
8. Las dependencias deben apuntar hacia las capas internas; no se crearán ciclos entre carpetas.

## 8.3. Flujo de una solicitud

```mermaid
flowchart TD
    A[Angular web o móvil] --> B[routers / FastAPI]
    B --> C[core: autenticación y permisos]
    B --> D[schemas: validación del contrato]
    C --> E[services: casos de uso]
    D --> E
    E --> F[repositories: consultas y persistencia]
    F --> G[tables.py: entidades SQLAlchemy]
    G --> H[(PostgreSQL)]
    H --> G
    G --> F
    F --> E
    E --> I[schemas de respuesta]
    I --> J[Respuesta HTTP]
    E -. OCR de órdenes .-> K[ai / RapidOCR]
```

Para las operaciones que modifican datos, el servicio que representa el caso de uso será el **límite de la transacción**. El servicio coordinará todas las escrituras y lecturas necesarias en una misma sesión. Los repositorios no harán `commit`; ante un error, el servicio dejará que la transacción se revierta y la API devolverá un error controlado.

## 8.4. Organización por responsabilidades de negocio

Aunque los archivos se agrupan por tipo técnico, cada capa conservará nombres y límites de negocio claros:

- Usuarios y autenticación: `auth`, `users`.
- Catálogos: `branches`, `catalogs`.
- Órdenes: `purchase_orders`.
- Vales: `vouchers`.
- Despachos: `attendances`.
- Verificación física: `verifications`.
- Saldos: `balances`.
- Reportes: `reports`.
- OCR de órdenes: `ocr`.

Los nombres se reflejarán en rutas, schemas, servicios y repositorios. No se crearán carpetas de dominio duplicadas ni se combinarán dos estilos de organización en el mismo proyecto.

## 8.5. Transacciones del dominio

`AttendanceService` será responsable de orquestar tanto la primera atención (creación de vale + líneas autorizadas + atención + detalles) como las atenciones posteriores. Utilizará los repositorios correspondientes dentro de una sola transacción PostgreSQL, bloqueará las líneas de orden y vale en orden determinista, validará los saldos actuales y confirmará todo junto.

`PurchaseOrderService` coordinará las modificaciones de órdenes y sus líneas, comprobando que no se reduzcan cantidades ni se eliminen líneas por debajo de consumos ya registrados. `VoucherVerificationService` registrará decisiones de Oficina sin modificar `attendance_items`. Estas reglas no deben implementarse en los routers ni en el frontend.

---

# 9. Estructura de directorios

Se utilizará una estructura **por capas y por tipo de responsabilidad**, siguiendo el estilo del árbol `back-fareas/` compartido y adaptándolo al dominio del sistema San José. La aplicación FastAPI estará dentro de `app/`; los archivos comunes de conexión y entidades serán `database.py` y `tables.py`.

```text
backend/
├── .agents/
│   └── skills/
│       └── fastapi/                    # Guías locales de desarrollo; no forman parte del runtime
├── app/
│   ├── ai/
│   │   └── rapidocr_engine.py          # Adaptador técnico de RapidOCR; sin lógica de negocio
│   ├── core/
│   │   ├── config.py                   # Settings y variables de entorno
│   │   ├── security.py                 # Hash de contraseñas y JWT
│   │   ├── permissions.py              # Roles y políticas predefinidas
│   │   ├── dependencies.py             # Usuario autenticado y dependencias de autorización
│   │   ├── exceptions.py               # Excepciones de aplicación/dominio
│   │   ├── error_handlers.py           # Traducción de excepciones a HTTP
│   │   ├── logging.py                  # Configuración de logs
│   │   ├── pagination.py               # Parámetros y metadatos de paginación
│   │   └── constants.py                # Constantes transversales
│   ├── routers/
│   │   ├── api_v1.py                   # Agrega los routers de /api/v1
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── branches.py
│   │   ├── catalogs.py
│   │   ├── purchase_orders.py
│   │   ├── vouchers.py
│   │   ├── attendances.py
│   │   ├── verifications.py
│   │   ├── balances.py
│   │   ├── reports.py
│   │   └── ocr.py
│   ├── schemas/
│   │   ├── common.py                   # Respuestas y paginación comunes
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── branch.py
│   │   ├── catalog.py
│   │   ├── purchase_order.py
│   │   ├── voucher.py
│   │   ├── attendance.py
│   │   ├── verification.py
│   │   ├── balance.py
│   │   ├── report.py
│   │   └── ocr.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── branch_service.py
│   │   ├── catalog_service.py
│   │   ├── purchase_order_service.py
│   │   ├── voucher_service.py
│   │   ├── attendance_service.py
│   │   ├── voucher_verification_service.py
│   │   ├── balance_service.py
│   │   ├── report_service.py
│   │   ├── report_export_service.py
│   │   └── purchase_order_ocr_service.py
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── auth_session_repository.py
│   │   ├── branch_repository.py
│   │   ├── fuel_type_repository.py
│   │   ├── purchase_order_repository.py
│   │   ├── purchase_order_item_repository.py
│   │   ├── voucher_repository.py
│   │   ├── voucher_item_repository.py
│   │   ├── attendance_repository.py
│   │   ├── verification_repository.py
│   │   ├── balance_repository.py
│   │   └── report_repository.py
│   ├── database.py                     # Engine, SessionLocal, get_db y ciclo de vida
│   ├── tables.py                       # Base y entidades SQLAlchemy del sistema
│   └── main.py                         # Creación y configuración de FastAPI
├── alembic/
│   ├── versions/                       # Migraciones versionadas
│   └── env.py
├── db/
│   └── README.md                       # Convenciones y notas de base de datos; Alembic es la fuente del esquema
├── scripts/
│   ├── check_db.py                     # Diagnóstico de conexión
│   ├── seed_catalogs.py                # Carga inicial controlada de sedes y combustibles
│   └── create_admin.py                 # Alta segura del primer administrador
├── storage/
│   └── ocr_tmp/                        # Temporales de OCR; ignorados por Git y limpiados
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── concurrency/
│   └── conftest.py
├── .env.example
├── .gitignore
├── pyproject.toml                      # Configuración de proyecto y herramientas
├── requirements.txt                    # Dependencias con versiones fijadas
├── requirements-dev.txt                # Dependencias de desarrollo y pruebas
├── alembic.ini
├── Dockerfile
├── compose.yaml
└── README.md
```

### 9.1. Criterios de adaptación

- `app/ai/` contiene únicamente la integración técnica necesaria para RapidOCR. No se incorporan reconocimiento facial, detección facial ni procesamiento de imágenes ajenos a los RF.
- `app/routers/` agrupa las rutas HTTP por recurso funcional. `api_v1.py` agrega los routers y aplica el prefijo `/api/v1`.
- `app/schemas/` centraliza los DTO Pydantic de requests y responses, separados por recurso.
- `app/services/` implementa los casos de uso. Sus nombres expresan acciones del negocio, no operaciones HTTP.
- `app/repositories/` encapsula SQLAlchemy. Se añade porque el control concurrente de saldos, los joins y los reportes necesitan consultas de persistencia aisladas; no es una carpeta de endpoints. Sus archivos deben cubrir los repositorios enumerados en la sección 17, incluidos los de líneas de orden, líneas de vale y saldos.
- `app/database.py` administra conexiones y sesiones. Se conserva SQLAlchemy 2.x síncrono, como establece ADR-003; no se mezclará una sesión asíncrona con operaciones síncronas. `app/tables.py` concentra las entidades SQLAlchemy y restricciones relacionales para mantener una única definición del esquema ORM.
- `alembic/` es la única fuente de migraciones versionadas. No duplicar el esquema en scripts SQL manuales dentro de `db/`.
- `db/` puede contener documentación o SQL auxiliar de diagnóstico, pero no una segunda secuencia de migraciones.
- `storage/ocr_tmp/` es temporal, no persistente y debe estar incluido en `.gitignore`. La aplicación debe eliminar cada archivo temporal incluso cuando OCR falle.
- `.agents/skills/fastapi/` es documentación local opcional para asistentes/desarrolladores; no debe ser dependencia del backend ni contener secretos.
- No se incluye `frontend.py`: el frontend Angular se mantiene como aplicación independiente, salvo que una decisión de despliegue futura requiera servir sus archivos estáticos desde FastAPI.
- No se recomienda mantener dos puntos de entrada. El comando de desarrollo/producción será `uvicorn app.main:app`.

### 9.2. Reglas para no sobredimensionar la estructura

Crear los archivos cuando la fase correspondiente los necesite. No generar módulos vacíos. Si un recurso tiene pocas consultas, no se necesita un repositorio artificial: puede compartir un repositorio de catálogo mientras siga existiendo una responsabilidad clara. No crear una capa `utils/` genérica para funciones sin relación; las utilidades transversales van en `core/` y las específicas permanecen junto al servicio que las usa.

---

# 10. Convenciones de nomenclatura

## 10.1. Idioma

Inglés para tablas, columnas, rutas, parámetros, archivos, carpetas, clases, funciones, variables, modelos, schemas, servicios, repositorios y enums. Los mensajes dirigidos al usuario pueden estar en español.

## 10.2. Python

| Elemento | Convención | Ejemplo |
|---|---|---|
| Variables y funciones | `snake_case` | `available_gallons`, `calculate_balance()` |
| Clases | `PascalCase` | `AttendanceService` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_PDF_BYTES` |
| Archivos | `snake_case` | `attendance_service.py` |
| Schemas | `PascalCase` | `AttendanceCreate` |

## 10.3. Base de datos

- Tablas en plural y `snake_case`.
- Columnas en singular y `snake_case`.
- PK `id`; FK `<referenced_table_singular>_id`.
- Tiempos `created_at`, `updated_at`, `attended_at`, `reviewed_at`.
- Borrado lógico `deleted_at` únicamente en órdenes que puedan eliminarse sin dependencias y en cuentas cuando corresponda.
- Restricciones `uq_`, `fk_`, `ck_`; índices `ix_`.
- Cantidades/precios con `NUMERIC`, nunca `FLOAT`.
- UUID para identificadores internos.
- Números de documento como `VARCHAR` para preservar ceros iniciales y formatos.

## 10.4. API

- Prefijo `/api/v1`.
- Recursos en plural: `/purchase-orders`, `/vouchers`, `/attendances`.
- `kebab-case` en nombres de recursos compuestos.
- Identificadores en path parameters.
- Filtros, búsqueda, ordenamiento y paginación en query parameters.
- `POST` crea; `GET` consulta; `PATCH` modifica parcialmente; `DELETE` aplica la política de eliminación condicionada.
- No crear rutas de comparación de períodos ni de impresión.

## 10.5. JSON

Usar `snake_case`. Cantidades e importes deben transportarse con precisión decimal. Se recomienda serializar decimales como strings (`"5.000"`) de forma consistente para evitar pérdida de precisión en clientes TypeScript. La decisión final se reflejará en OpenAPI y no se mezclarán strings y números para el mismo campo.

---

# 11. Diseño de base de datos

## 11.1. Criterios del modelo

El modelo seguirá esta secuencia:

`PurchaseOrder -> PurchaseOrderItem -> VoucherItem -> AttendanceItem -> Attendance`

La cabecera de `Voucher` representa el documento físico. Sus líneas representan cantidades autorizadas por tipo de combustible. Una `Attendance` representa un evento de despacho realizado en una visita y sus `AttendanceItems` contienen los galones realmente entregados por línea.

Esta estructura permite:

- Una orden con distintos tipos de combustible.
- Un vale con una o varias líneas de combustible.
- Un vale con múltiples atenciones parciales.
- Una atención que incluya cantidades de más de un tipo de combustible.
- Cálculos por línea sin mezclar unidades de combustible.

**No se almacenarán saldos editables.** Se obtendrán con agregaciones de los detalles de atención. Si en el futuro se incorpora una tabla de saldos materializados por rendimiento, deberá mantenerse mediante transacciones y reconciliación automática; no forma parte de la primera versión.

## 11.2. Diagrama entidad-relación lógico

```mermaid
erDiagram
    BRANCHES ||--o{ USERS : assigned_to
    BRANCHES ||--o{ PURCHASE_ORDERS : supplier_branch
    BRANCHES ||--o{ ATTENDANCES : served_at
    USERS ||--o{ ATTENDANCES : performs
    USERS ||--o{ ATTENDANCE_VERIFICATIONS : reviews
    USERS ||--o{ AUTH_SESSIONS : owns
    PURCHASE_ORDERS ||--|{ PURCHASE_ORDER_ITEMS : contains
    FUEL_TYPES ||--o{ PURCHASE_ORDER_ITEMS : classifies
    PURCHASE_ORDERS ||--o{ VOUCHERS : receives
    VOUCHERS ||--|{ VOUCHER_ITEMS : authorizes
    PURCHASE_ORDER_ITEMS ||--o{ VOUCHER_ITEMS : limits
    VOUCHERS ||--o{ ATTENDANCES : receives
    ATTENDANCES ||--|{ ATTENDANCE_ITEMS : contains
    VOUCHER_ITEMS ||--o{ ATTENDANCE_ITEMS : consumes
    ATTENDANCES ||--o{ ATTENDANCE_VERIFICATIONS : reviewed_by

    BRANCHES {
      uuid id PK
      varchar code UK
      varchar name UK
      boolean is_active
    }
    USERS {
      uuid id PK
      varchar dni UK
      varchar email UK
      varchar role
      uuid branch_id FK
      boolean is_active
    }
    PURCHASE_ORDERS {
      uuid id PK
      varchar order_number
      varchar executing_unit_ruc
      date issue_date
      timestamptz deleted_at
    }
    PURCHASE_ORDER_ITEMS {
      uuid id PK
      uuid purchase_order_id FK
      uuid fuel_type_id FK
      numeric authorized_gallons
      numeric unit_price
      numeric total_amount
    }
    VOUCHERS {
      uuid id PK
      uuid purchase_order_id FK
      varchar issuer_type
      varchar issuer_name
      varchar voucher_number
    }
    VOUCHER_ITEMS {
      uuid id PK
      uuid voucher_id FK
      uuid purchase_order_item_id FK
      numeric authorized_gallons
    }
    ATTENDANCES {
      uuid id PK
      uuid voucher_id FK
      uuid performed_by_user_id FK
      uuid branch_id FK
      uuid idempotency_key UK
      timestamptz attended_at
    }
    ATTENDANCE_ITEMS {
      uuid id PK
      uuid attendance_id FK
      uuid voucher_item_id FK
      numeric attended_gallons
      numeric unit_price_snapshot
    }
    ATTENDANCE_VERIFICATIONS {
      uuid id PK
      uuid attendance_id FK
      uuid reviewed_by_user_id FK
      varchar decision
      timestamptz reviewed_at
    }
    AUTH_SESSIONS {
      uuid id PK
      uuid user_id FK
      varchar jti UK
      timestamptz expires_at
      timestamptz revoked_at
    }
```

## 11.3. `branches`

**Propósito:** catálogo central de sedes.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `code` | VARCHAR(20) | NOT NULL, UNIQUE | Código corto. |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | Nombre visible. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Estado operativo. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |

Seeds iniciales: `SAN_JOSE` y `SANTA_MARTA`. No crear CRUD de sedes, porque no existe RF para administrar este catálogo.

## 11.4. `users`

**Propósito:** cuentas internas, rol y sede habitual.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `first_name` | VARCHAR(100) | NOT NULL | Nombres. |
| `last_name` | VARCHAR(150) | NOT NULL | Apellidos. |
| `dni` | VARCHAR(20) | NOT NULL, UNIQUE | DNI como texto. |
| `email` | VARCHAR(254) | NOT NULL, UNIQUE | Correo/login. |
| `password_hash` | VARCHAR(255) | NOT NULL | Hash Argon2. |
| `role` | VARCHAR(20) | NOT NULL, CHECK | `ADMIN`, `OFFICE`, `ATTENDANT`. |
| `branch_id` | UUID | FK, NULL según rol | Sede habitual; obligatoria para Grifero según la propuesta. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Habilitación. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Modificación. |

DNI y correo únicos. El usuario no puede autoasignarse rol. Un usuario deshabilitado no inicia sesión y las sesiones activas se revocan. No se borra físicamente una cuenta que ya tenga registros operativos.

## 11.5. `auth_sessions`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Sesión. |
| `user_id` | UUID | FK, NOT NULL | Propietario. |
| `jti` | VARCHAR(64) | NOT NULL, UNIQUE | Identificador JWT. |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Vencimiento. |
| `revoked_at` | TIMESTAMPTZ | NULL | Revocación/logout. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Inicio. |

No almacenar el JWT completo. Se valida firma, vencimiento, revocación y estado activo del usuario.

## 11.6. `fuel_types`

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `code` | VARCHAR(30) | NOT NULL, UNIQUE | Código interno. |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | Nombre del combustible. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Disponible para nuevas líneas. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |

La estación debe validar la lista inicial de tipos de combustible. `DIESEL S50` es un ejemplo de los RF, no el único combustible. Los valores se cargarán mediante seeds.

## 11.7. `purchase_orders`

**Propósito:** cabecera de orden de compra. No se implementa auditoría de autoría/modificación de la orden, porque el levantamiento no la requiere.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador interno. |
| `order_number` | VARCHAR(60) | NOT NULL | Número documental. |
| `siaf_number` | VARCHAR(60) | NOT NULL | Expediente SIAF. |
| `issue_date` | DATE | NOT NULL | Fecha documental. |
| `institution_name` | VARCHAR(200) | NOT NULL | Entidad/institución. |
| `supplier_name` | VARCHAR(200) | NOT NULL | Proveedor. |
| `supplier_details` | TEXT | NULL | Detalle adicional no estructurado mientras se define el formato final. |
| `executing_unit` | VARCHAR(200) | NOT NULL | Unidad ejecutora. |
| `executing_unit_ruc` | VARCHAR(20) | NOT NULL | RUC indicado para la unidad ejecutora. |
| `branch_id` | UUID | FK, NOT NULL | Sede proveedora indicada en la orden. |
| `deleted_at` | TIMESTAMPTZ | NULL | Eliminación lógica condicionada. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Modificación. |

Índices: `issue_date`, `order_number`, `executing_unit_ruc`, `institution_name`, `branch_id`. Restricción única propuesta: `(executing_unit_ruc, order_number)`; debe confirmarse PD-001.

Los campos de proveedor no se ampliarán con datos fiscales que no estén en los RF. `supplier_name` será el mínimo estructurado y `supplier_details` mantendrá datos adicionales mientras el negocio define el formulario.

## 11.8. `purchase_order_items`

**Propósito:** cantidades y precios por tipo de combustible.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador de la línea. |
| `purchase_order_id` | UUID | FK, NOT NULL | Orden. |
| `fuel_type_id` | UUID | FK, NOT NULL | Tipo de combustible. |
| `authorized_gallons` | NUMERIC(14,3) | NOT NULL, CHECK > 0 | Galones autorizados. |
| `unit_price` | NUMERIC(14,4) | NOT NULL, CHECK >= 0 | Precio unitario documental. |
| `total_amount` | NUMERIC(14,2) | NOT NULL, CHECK >= 0 | Precio total documental. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Modificación. |

Una orden tendrá una o más líneas. No se agregan saldos por tipo distinto. No asumir todavía que `total_amount` siempre es cantidad × precio unitario: la regla de redondeo y posibles conceptos documentales están pendientes en PD-020. La aplicación validará que valores y cantidades sean no negativos/positivos según corresponda.

Se requiere una clave única compuesta `(id, purchase_order_id)` para reforzar las relaciones compuestas desde los vales.

## 11.9. `vouchers`

**Propósito:** representar el documento físico presentado por el cliente. Se crea durante la primera atención, no antes.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador interno. |
| `purchase_order_id` | UUID | FK, NOT NULL | Orden a la que pertenece. |
| `issuer_type` | VARCHAR(20) | NOT NULL, CHECK | `INSTITUTION` o `STATION`. |
| `issuer_name` | VARCHAR(200) | NOT NULL | Entidad emisora o Estación. |
| `issuer_normalized` | VARCHAR(200) | NOT NULL | Valor normalizado para unicidad. |
| `voucher_number` | VARCHAR(60) | NOT NULL | Número visible del vale. |
| `voucher_number_normalized` | VARCHAR(60) | NOT NULL | Número normalizado para búsquedas/duplicados. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Última corrección descriptiva. |

No se almacenan cantidades ni saldo directamente en cabecera; esas cantidades viven en `voucher_items`. Se almacenan datos de emisor para resolver numeraciones de instituciones y de la estación. El responsable de la primera captura se obtiene desde la primera atención relacionada, sin duplicar una columna de auditoría en la cabecera.

Restricciones de unicidad propuestas:

- Vales institucionales: `(purchase_order_id, issuer_type, issuer_normalized, voucher_number_normalized)`.
- Vales emitidos por la estación: `voucher_number_normalized` único en la serie central de estación, si se confirma que la numeración es global.

Los índices parciales PostgreSQL deberán aplicar la regla de unicidad por tipo de emisor. Confirmar el alcance exacto de numeración mediante PD-002.

## 11.10. `voucher_items`

**Propósito:** cantidad autorizada de cada tipo/línea de combustible dentro del vale.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `voucher_id` | UUID | FK, NOT NULL | Cabecera del vale. |
| `purchase_order_id` | UUID | FK compuesta, NOT NULL | Orden común. |
| `purchase_order_item_id` | UUID | FK compuesta, NOT NULL | Línea de orden que autoriza el combustible. |
| `authorized_gallons` | NUMERIC(14,3) | NOT NULL, CHECK > 0 | Galones indicados en el vale para esta línea. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |

Cada línea del vale se vincula a una línea de la orden y, por tanto, a un tipo de combustible. Las FK compuestas deben impedir que una línea de vale de una orden se relacione accidentalmente con una línea de otra orden. Restricción única `(voucher_id, purchase_order_item_id)` evita duplicar el mismo combustible/línea en la cabecera.

No se creará una tabla de vales previa en estado borrador: el vale operativo nace dentro de la primera atención.

## 11.11. `attendances`

**Propósito:** representar cada evento o visita en que se despacha combustible contra un vale. Un vale puede tener muchas atenciones.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `voucher_id` | UUID | FK, NOT NULL | Vale atendido. |
| `performed_by_user_id` | UUID | FK, NOT NULL | Usuario autenticado que ejecutó el despacho (normalmente el grifero; ADMIN también está autorizado por la matriz V2). |
| `branch_id` | UUID | FK, NOT NULL | Sede desde la que se despachó. |
| `attended_at` | TIMESTAMPTZ | NOT NULL | Fecha/hora del servidor en UTC. |
| `idempotency_key` | UUID | NOT NULL, UNIQUE | Evita duplicados por reintento. |
| `request_fingerprint` | VARCHAR(64) | NOT NULL | Hash del payload para detectar reutilización de clave con otra solicitud. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Registro técnico. |

No debe existir restricción `UNIQUE(voucher_id)`: esa restricción impediría atenciones parciales. Se usará FK no única `voucher_id` y relación uno a muchos.

## 11.12. `attendance_items`

**Propósito:** cantidades reales despachadas en cada evento, separadas por línea de vale/tipo de combustible.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `attendance_id` | UUID | FK, NOT NULL | Evento de atención. |
| `voucher_item_id` | UUID | FK, NOT NULL | Línea autorizada consumida. |
| `attended_gallons` | NUMERIC(14,3) | NOT NULL, CHECK > 0 | Cantidad real entregada en esta atención. |
| `unit_price_snapshot` | NUMERIC(14,4) | NOT NULL, CHECK >= 0 | Precio unitario de la línea de orden al momento de atender. |
| `attended_amount` | NUMERIC(14,2) | NOT NULL, CHECK >= 0 | Importe calculado según precio snapshot y galones, sujeto a regla de redondeo PD-020. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Alta. |

Restricción única `(attendance_id, voucher_item_id)` para que una atención agrupe una sola línea por cada combustible del vale. Añadir una FK compuesta que garantice que `attendance_id` y `voucher_item_id` pertenecen al mismo `voucher_id` (mediante `voucher_id` redundante controlado o una clave compuesta equivalente); no depender exclusivamente de una validación de servicio. Si el cliente recibe más combustible en una visita posterior, se genera otra atención con nuevos detalles.

El precio snapshot permite reportar el importe histórico de lo atendido aunque el precio de la orden cambie posteriormente. PD-009 debe confirmar qué interpretación exacta requiere el negocio para el “precio atendido por hora”.

## 11.13. `attendance_verifications`

**Propósito:** conservar la verificación administrativa de cada atención contra el vale físico. Es un historial específico de este flujo, no una auditoría general de todas las acciones.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `attendance_id` | UUID | FK, NOT NULL | Atención revisada. |
| `reviewed_by_user_id` | UUID | FK, NOT NULL | Usuario Oficina o Administrador. |
| `decision` | VARCHAR(20) | NOT NULL, CHECK | `VERIFIED` o `OBSERVED`. |
| `observation` | TEXT | NULL | Obligatoria cuando se observa una diferencia. |
| `reviewed_at` | TIMESTAMPTZ | NOT NULL | Fecha/hora servidor. |

Se permiten varias revisiones para una atención si inicialmente fue observada y luego se vuelve a comprobar. El estado actual de verificación se obtiene de la última revisión. La verificación nunca actualiza `attendance_items`.

## 11.14. `document_counters` (propuesta)

**Propósito:** asignar el número correlativo central para vales emitidos por la estación cuando el negocio confirme el formato de numeración.

| Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador. |
| `counter_code` | VARCHAR(40) | NOT NULL, UNIQUE | Serie/código de numeración. |
| `last_value` | BIGINT | NOT NULL, CHECK >= 0 | Último valor asignado. |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Última asignación. |

La fila se bloqueará dentro de la misma transacción que crea el vale. El formato final y si la numeración es global o por serie debe confirmarse con PD-002. Si no se requiere control transaccional sin huecos, podrá utilizarse una secuencia PostgreSQL estándar.

## 11.15. Integridad referencial

- `purchase_orders -> purchase_order_items`: `ON DELETE RESTRICT`.
- `purchase_orders -> vouchers`: `ON DELETE RESTRICT`.
- `vouchers -> voucher_items`: `ON DELETE RESTRICT`.
- `vouchers -> attendances`: `ON DELETE RESTRICT`.
- `voucher_items -> attendance_items`: `ON DELETE RESTRICT`.
- `attendances -> attendance_verifications`: `ON DELETE RESTRICT`.
- `users -> attendances`: `ON DELETE RESTRICT`.
- `users -> attendance_verifications`: `ON DELETE RESTRICT`.
- `branches -> users`, `purchase_orders` y `attendances`: `ON DELETE RESTRICT`.

Nunca usar `ON DELETE CASCADE` sobre órdenes, vales, atenciones o verificaciones.

## 11.16. Fórmulas de saldo

Para una línea de vale:

```text
voucher_item_attended = SUM(attendance_items.attended_gallons)
                        de todas las atenciones que consumen esa voucher_item

voucher_item_balance = voucher_item.authorized_gallons
                       - voucher_item_attended
```

Para una línea de orden:

```text
order_item_attended = SUM(attendance_items.attended_gallons)
                      de todas las líneas de vale asociadas a esa order_item

order_item_balance = purchase_order_item.authorized_gallons
                     - order_item_attended
```

Para una orden:

```text
purchase_order_status = AVAILABLE si existe alguna línea con balance > 0
                        DEPLETED si todas las líneas tienen balance = 0
```

**Prohibido:** calcular `order_item_balance` restando `voucher_items.authorized_gallons`. La autorización del vale no es consumo. El único descuento de orden es `attendance_items.attended_gallons`.

No se aceptarán cantidades en saldo dentro de requests de escritura. Los saldos de la respuesta deberán calcularse en base a registros persistidos.

---

# 12. Modelos SQLAlchemy

| Clase | Tabla | Relaciones principales |
|---|---|---|
| `Branch` | `branches` | Usuarios, órdenes y atenciones. |
| `User` | `users` | Sede, sesiones, atenciones y verificaciones. |
| `AuthSession` | `auth_sessions` | Usuario. |
| `FuelType` | `fuel_types` | Líneas de orden. |
| `PurchaseOrder` | `purchase_orders` | Sede, creador, líneas y vales. |
| `PurchaseOrderItem` | `purchase_order_items` | Orden, combustible y líneas de vales. |
| `Voucher` | `vouchers` | Orden, creador, líneas y atenciones. |
| `VoucherItem` | `voucher_items` | Vale, línea de orden y detalles de atención. |
| `Attendance` | `attendances` | Vale, grifero, sede, detalles y verificaciones. |
| `AttendanceItem` | `attendance_items` | Atención y línea de vale. |
| `AttendanceVerification` | `attendance_verifications` | Atención y revisor. |
| `DocumentCounter` | `document_counters` | Serie de numeración de vales de estación. |

Reglas de implementación:

- Usar `Mapped[]`, `mapped_column()` y `relationship()` de SQLAlchemy 2.x.
- UUID para IDs y `Numeric` para cantidades/precios/importes.
- Definir `CheckConstraint`, `UniqueConstraint`, índices y FK compuestas.
- No persistir `available_gallons` como campo editable.
- No crear entidad `Role` separada mientras existan tres valores fijos; los permisos se definen en código como política versionada.
- No crear tablas para dashboard, reportes o previews OCR temporales.
- No habilitar cascadas destructivas en relaciones operativas.

Enums propuestos:

```text
UserRole: ADMIN, OFFICE, ATTENDANT
VoucherIssuerType: INSTITUTION, STATION
OrderBalanceStatus: AVAILABLE, DEPLETED
VoucherItemStatus: PENDING, PARTIALLY_ATTENDED, COMPLETED, BLOCKED_BY_ORDER_BALANCE
VoucherStatus: PENDING, PARTIALLY_ATTENDED, COMPLETED, PARTIALLY_BLOCKED
VerificationDecision: VERIFIED, OBSERVED
```

Los estados de saldo son valores derivados para respuestas; no se cambian manualmente ni deben convertirse en campos de control modificables.

---

# 13. Esquemas Pydantic

Separar schemas de creación, actualización, filtro y respuesta. No reutilizar un schema de respuesta para escritura.

## 13.1. Usuarios y autenticación

- `UserCreate`: nombres, apellidos, DNI, correo, contraseña inicial, rol y sede cuando aplique.
- `UserUpdate`: campos de perfil permitidos.
- `UserStatusUpdate`: habilitar/deshabilitar.
- `UserRoleUpdate`: rol nuevo, si se permite cambio de rol después del alta.
- `UserResponse`: datos públicos, rol, sede y estado; nunca password/hash.
- `LoginRequest`, `TokenResponse`, `CurrentUserResponse`.

El contrato debe incluir los permisos efectivos del rol en `CurrentUserResponse` o permitir consultarlos mediante `/auth/me` para construir la navegación del frontend.

## 13.2. Órdenes

- `PurchaseOrderCreate`: cabecera y arreglo no vacío `items`.
- `PurchaseOrderUpdate`: campos editables y arreglo de líneas sujeto a reglas de integridad.
- `PurchaseOrderItemCreate`: `fuel_type_id`, `authorized_gallons`, `unit_price`, `total_amount`.
- `PurchaseOrderItemResponse`: datos de línea, galones atendidos, saldo y estado derivado.
- `PurchaseOrderResponse`: cabecera, líneas, saldo por tipo de combustible y estado agregado.
- `PurchaseOrderFilters`: `search`, institución, número, fecha, estado, sede, página y orden.

## 13.3. Vales

- `VoucherIdentityCreate`: `issuer_type`, `issuer_name`, `voucher_number` cuando sea institucional.
- `VoucherItemCreate`: `purchase_order_item_id`, `authorized_gallons`.
- `VoucherResponse`: emisor, número, orden, líneas, autorizados, atendidos, saldos, estados y atenciones.
- `VoucherDescriptiveUpdate`: solo campos descriptivos aprobados para corrección por Administrador.
- `VoucherFilters`: número de vale, número de orden, entidad/institución, fecha, estado de consumo y verificación.

No debe existir `VoucherCreate` como operación normal independiente de registro previo. El schema para crear el vale se incluirá dentro de `InitialAttendanceCreate`.

## 13.4. Atenciones

- `InitialAttendanceCreate`: cabecera del vale nuevo, todas sus líneas autorizadas y un arreglo separado `attendance_items` con las cantidades realmente entregadas en la primera visita.
- `InitialVoucherItemInput`: `purchase_order_item_id` y `authorized_gallons`; representa la autorización documental, no el consumo de la visita.
- `InitialAttendanceItemInput`: `purchase_order_item_id` y `attended_gallons`; incluye únicamente líneas que recibieron combustible en esta visita y exige cantidad mayor que cero.
- `VoucherAttendanceCreate`: líneas de vale existentes (`voucher_item_id`) y cantidad real a despachar en esta visita.
- `AttendanceItemResponse`: galones reales, tipo de combustible y precio snapshot.
- `AttendanceResponse`: usuario, sede, fecha/hora, vale, detalles y saldos resultantes.
- `AttendanceFilters`: fecha, usuario, sede, vale, orden, combustible y estado de verificación.

La fecha/hora, el usuario y la sede se obtienen del contexto autenticado y del servidor, nunca del body recibido.

## 13.5. Verificaciones

- `AttendanceVerificationCreate`: decisión `VERIFIED` u `OBSERVED`, comentario opcional/obligatorio según decisión.
- `AttendanceVerificationResponse`: decisión, revisor, fecha/hora y observación.
- `PendingVerificationFilters`: fecha, grifero, sede, orden, vale y estado actual.

Para `OBSERVED`, `observation` debe ser obligatoria y no vacía.

## 13.6. Saldos y reportes

- `VoucherItemBalanceResponse`.
- `OrderItemBalanceResponse`.
- `PurchaseOrderBalanceResponse`.
- `VoucherBalanceResponse`.
- `DashboardResponse`.
- `PurchaseOrderReportFilters`.
- `AttendanceReportFilters`.
- `HourlyAttendanceSeries`, `DailyAttendanceSeries`, `WeeklyAttendanceSeries`, `MonthlyAttendanceSeries`.
- `ReportRowResponse`.

Los rangos serán `date_from` y `date_to`; validar `date_from <= date_to`. Los filtros por estados deben usar los enums vigentes.

## 13.7. OCR

- `OcrPreviewResponse`: campos reconocidos y lista de observaciones.
- `OcrFieldCandidate`: `field_name`, `value`, `confidence` cuando el motor lo proporcione, `page_number` y texto de origen cuando sea posible.
- `OcrErrorResponse`: formato inválido, archivo dañado, PDF protegido, límite excedido o error de procesamiento.

El resultado OCR es una previsualización, no una entidad `PurchaseOrder` ni un comando de persistencia.

---

# 14. Diseño de API REST

## 14.1. Convenciones generales

- Base URL `/api/v1`.
- JWT Bearer en rutas privadas.
- JSON en operaciones ordinarias.
- `multipart/form-data` únicamente para PDF OCR.
- Decimales con formato consistente.
- Fechas documentales `YYYY-MM-DD`.
- Timestamps ISO 8601 con zona; la persistencia será UTC.
- Listados paginados.
- Filtros y ordenamiento por whitelist.
- No devolver información administrativa sensible al Grifero.
- OpenAPI será la fuente del cliente Angular cuando el backend esté implementado.

## 14.2. Catálogo de endpoints

### Salud

| Método | Endpoint | Descripción | Auth |
|---|---|---|---|
| GET | `/api/v1/health/live` | Proceso activo. | No |
| GET | `/api/v1/health/ready` | Disponibilidad de aplicación y DB. | No, respuesta mínima |

### Autenticación y usuarios

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Iniciar sesión. | RF-003 | Público |
| POST | `/api/v1/auth/logout` | Revocar sesión propia. | RF-005 | Usuario autenticado |
| GET | `/api/v1/auth/me` | Usuario actual, rol y permisos efectivos. | RF-002/RF-003 | Usuario autenticado |
| GET | `/api/v1/users` | Listar cuentas. | RF-001/RF-004 | `users.read` |
| POST | `/api/v1/users` | Crear cuenta y asignar rol. | RF-001/RF-002 | `users.create` |
| GET | `/api/v1/users/{user_id}` | Consultar cuenta. | RF-001/RF-004 | `users.read` |
| PATCH | `/api/v1/users/{user_id}/role` | Cambiar rol predefinido, si se habilita esta acción. | RF-002 | `users.manage_roles` |
| PATCH | `/api/v1/users/{user_id}/status` | Habilitar/deshabilitar cuenta. | RF-004 | `users.manage_status` |
| GET | `/api/v1/users/{user_id}/attendances` | Consultar atenciones del grifero. | RF-006 | `attendances.read_all` |

No se implementará `DELETE /users/{id}` como borrado físico. La interfaz utilizará el endpoint de estado. Un usuario deshabilitado conserva la autoría de sus órdenes, verificaciones y atenciones.

### Catálogos

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/branches` | Listar sedes. | RF-025 | Autenticado |
| GET | `/api/v1/fuel-types` | Listar combustibles activos. | RF-007/RF-019 | Autenticado |

No crear CRUD de catálogos sin aprobación funcional.

### Órdenes de compra

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/purchase-orders` | Buscar, filtrar, ordenar y paginar órdenes. | RF-009/RF-010/RF-032 | `purchase_orders.read` |
| POST | `/api/v1/purchase-orders` | Registrar orden y sus líneas. | RF-007 | `purchase_orders.create` |
| GET | `/api/v1/purchase-orders/{order_id}` | Detalle de cabecera, líneas, vales y saldos. | RF-008 | `purchase_orders.read` |
| PATCH | `/api/v1/purchase-orders/{order_id}` | Modificar datos y líneas permitidas. | RF-011 | `purchase_orders.update` |
| DELETE | `/api/v1/purchase-orders/{order_id}` | Eliminación lógica solo si no tiene vales. | RF-012 | `purchase_orders.delete` |

### Consulta de vales y atenciones

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/vouchers` | Buscar por número de vale, orden, entidad y filtros; paginar/ordenar. | RF-015/RF-016/RF-033 | `vouchers.read` |
| GET | `/api/v1/vouchers/{voucher_id}` | Consultar documento, líneas, atenciones y saldos. | RF-014/RF-015 | `vouchers.read` |
| PATCH | `/api/v1/vouchers/{voucher_id}/descriptive-data` | Corregir campos descriptivos permitidos. | RF-017 | `vouchers.correct_descriptive_data` |
| DELETE | `/api/v1/vouchers/{voucher_id}` | Bloquear eliminación de vale atendido; responde conflicto. | RF-018 | `vouchers.delete_attempt` |
| GET | `/api/v1/attendances` | Listar atenciones según rol y alcance. | RF-006/RF-013/RF-028 | `attendances.read` |
| GET | `/api/v1/attendances/{attendance_id}` | Detalle de un despacho. | RF-006/RF-013 | `attendances.read` |
| POST | `/api/v1/purchase-orders/{order_id}/attendances` | Crear vale + líneas + primer despacho en una operación. | RF-019 | `attendances.create` |
| POST | `/api/v1/vouchers/{voucher_id}/attendances` | Registrar una atención parcial posterior del mismo vale. | RF-019 | `attendances.create` |

**No existe endpoint `POST /vouchers` para el alta normal de vales.** La creación del vale forma parte de la primera atención. Tampoco se crea un endpoint para que Oficina vuelva a registrar el documento.

### Verificación administrativa

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/attendances/pending-verification` | Listar atenciones pendientes u observadas para revisión. | RF-013 | `attendances.verify` |
| POST | `/api/v1/attendances/{attendance_id}/verifications` | Registrar resultado `VERIFIED` u `OBSERVED`. | RF-013 | `attendances.verify` |
| GET | `/api/v1/attendances/{attendance_id}/verifications` | Consultar historial de revisiones. | RF-013 | `attendances.verify` |

### Saldos

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/balances/purchase-orders/{order_id}` | Saldos por tipo/línea de combustible. | RF-020/RF-024/RF-025/RF-026 | `balances.read` |
| GET | `/api/v1/balances/vouchers/{voucher_id}` | Saldos por línea del vale. | RF-021/RF-024/RF-026 | `balances.read` |
| GET | `/api/v1/balances/overview` | Resumen de órdenes/saldos visibles para el usuario. | RF-024/RF-025 | `balances.read` |

### Reportes y dashboard

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| GET | `/api/v1/reports/purchase-orders` | Reporte de órdenes, combustibles y saldos. | RF-027/RF-029 | `reports.read` |
| GET | `/api/v1/reports/attendances` | Reporte de galones/importe atendido por periodo y agrupación. | RF-028/RF-029 | `reports.read` |
| GET | `/api/v1/dashboard` | Datos agregados para gráficos interactivos. | RF-030 | `reports.read` |
| GET | `/api/v1/reports/purchase-orders/export` | Exportar reporte de órdenes a PDF/XLSX. | RF-031 | `reports.export` |
| GET | `/api/v1/reports/attendances/export` | Exportar reporte de atenciones a PDF/XLSX. | RF-031 | `reports.export` |

No crear `/reports/comparison`, endpoints de impresión ni endpoints equivalentes. RF V2 los retiró expresamente.

### OCR

| Método | Endpoint | Descripción | RF | Permiso |
|---|---|---|---|---|
| POST | `/api/v1/ocr/purchase-order-previews` | Procesar PDF temporal y devolver campos candidatos para completar el formulario. | RF-034 | `ocr.process` |

El endpoint no persiste una orden y no acepta vales, fotografías ni otros formatos.

## 14.3. Detalle de operaciones críticas

### API-001 — Login

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "usuario@estacion.example",
  "password": "********"
}
```

Respuesta conceptual:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "role": "ATTENDANT",
    "branch": {
      "id": "uuid",
      "code": "SAN_JOSE",
      "name": "San José"
    },
    "permissions": ["purchase_orders.read", "balances.read", "attendances.create"]
  }
}
```

Proceso: buscar usuario por email; verificar cuenta activa y hash; crear sesión `jti`; firmar JWT; devolver los permisos asociados al rol. No revelar si el correo o contraseña fue el elemento incorrecto. El contrato final debe documentar expiración y revocación.

### API-002 — Crear una orden de compra

```http
POST /api/v1/purchase-orders
```

Request conceptual:

```json
{
  "order_number": "OC-001",
  "siaf_number": "SIAF-2026-001",
  "issue_date": "2026-11-12",
  "institution_name": "Institución de ejemplo",
  "supplier_name": "Estación de Servicio San José",
  "supplier_details": null,
  "executing_unit": "Unidad ejecutora",
  "executing_unit_ruc": "20123456789",
  "branch_id": "uuid",
  "items": [
    {
      "fuel_type_id": "uuid-diesel",
      "authorized_gallons": "100.000",
      "unit_price": "15.2500",
      "total_amount": "1525.00"
    },
    {
      "fuel_type_id": "uuid-gasoline",
      "authorized_gallons": "50.000",
      "unit_price": "16.1000",
      "total_amount": "805.00"
    }
  ]
}
```

Validar rol, campos obligatorios, sede, RUC, tipos activos, cantidades positivas y unicidad. Crear cabecera y todas las líneas dentro de una sola transacción. Si falla una línea, no debe quedar una orden parcial.

### API-003 — Primera atención: crear vale y despacho

```http
POST /api/v1/purchase-orders/{order_id}/attendances
Authorization: Bearer <token>
Idempotency-Key: <uuid>
```

Request conceptual para un vale nuevo:

```json
{
  "new_voucher": {
    "issuer_type": "INSTITUTION",
    "issuer_name": "Institución de ejemplo",
    "voucher_number": "000125",
    "items": [
      {
        "purchase_order_item_id": "uuid-diesel-line",
        "authorized_gallons": "10.000"
      },
      {
        "purchase_order_item_id": "uuid-gasoline-line",
        "authorized_gallons": "4.000"
      }
    ]
  },
  "attendance_items": [
    {
      "purchase_order_item_id": "uuid-diesel-line",
      "attended_gallons": "5.000"
    }
  ]
}
```

En este ejemplo el mismo vale autoriza dos tipos de combustible, pero en esta visita el cliente solo recibe 5 galones de Diesel. Se guardan las dos líneas autorizadas y una sola línea de atención para Diesel; la línea de Gasolina permanece pendiente con su saldo autorizado intacto. En una visita posterior podrá despacharse gasolina sin crear otro vale.

Pasos obligatorios:

1. Verificar usuario `ATTENDANT` o actor autorizado por política.
2. Iniciar transacción PostgreSQL.
3. Bloquear mediante `SELECT ... FOR UPDATE`, en orden determinista, las líneas de orden que aparecen en los detalles realmente despachados.
4. Validar que todas las líneas autorizadas y despachadas pertenecen a la orden indicada y que la orden está activa.
5. Normalizar emisor/número y verificar duplicidad del vale.
6. Si el vale ya existe, rechazar la creación duplicada con `409 VOUCHER_ALREADY_EXISTS` e incluir el ID del vale existente en `details`; el cliente deberá usar `POST /vouchers/{voucher_id}/attendances` para continuar.
7. Validar cantidad autorizada positiva y cantidad despachada mayor que cero para los detalles que se vayan a guardar.
8. Validar que cada despacho no supere autorización restante de la línea de vale ni saldo actual de la línea de orden.
9. Crear cabecera de vale, líneas autorizadas, cabecera de atención y detalles de atención.
10. Registrar grifero, sede y timestamp tomados del servidor/contexto autenticado.
11. Confirmar la transacción y devolver vale, atención y saldos resultantes.

Si cualquier paso falla, no se guarda vale ni atención ni cambia saldo alguno.

### API-004 — Atención posterior del mismo vale

```http
POST /api/v1/vouchers/{voucher_id}/attendances
Authorization: Bearer <token>
Idempotency-Key: <uuid>
```

Request conceptual:

```json
{
  "items": [
    {
      "voucher_item_id": "uuid-voucher-diesel-line",
      "attended_gallons": "2.000"
    }
  ]
}
```

Proceso:

1. Iniciar transacción.
2. Obtener el vale y sus líneas.
3. Bloquear las líneas de orden relacionadas en orden determinista.
4. Bloquear el vale y sus líneas de autorización.
5. Recalcular los saldos dentro de la transacción.
6. Validar que cada cantidad sea positiva y no supere saldo de vale ni saldo de la línea de orden.
7. Insertar una nueva `Attendance` y sus `AttendanceItems`.
8. Tomar usuario, sede y fecha/hora del servidor.
9. Confirmar y devolver los nuevos saldos.

El número del vale no se vuelve a crear y la cantidad autorizada original no se sustituye. Un vale puede tener N atenciones, pero no puede exceder su autorización acumulada ni el total de la línea de orden.

### API-005 — Verificar vale físico en Oficina

```http
POST /api/v1/attendances/{attendance_id}/verifications
```

Request cuando coincide:

```json
{
  "decision": "VERIFIED",
  "observation": null
}
```

Request cuando hay diferencia:

```json
{
  "decision": "OBSERVED",
  "observation": "El número de vale del documento físico no coincide."
}
```

Validar rol `OFFICE` o `ADMIN`. Guardar usuario revisor, fecha/hora y decisión. Si el resultado es `OBSERVED`, exigir observación. Esta operación no toca `attendances`, `attendance_items` ni saldos.

### API-006 — Consulta de saldo de orden

```http
GET /api/v1/balances/purchase-orders/{order_id}
```

Respuesta conceptual:

```json
{
  "purchase_order_id": "uuid",
  "order_number": "OC-001",
  "status": "AVAILABLE",
  "items": [
    {
      "purchase_order_item_id": "uuid-diesel-line",
      "fuel_type": "DIESEL S50",
      "authorized_gallons": "100.000",
      "attended_gallons": "35.000",
      "available_gallons": "65.000",
      "status": "AVAILABLE"
    }
  ]
}
```

La respuesta al Grifero debe omitir precios unitarios, totales y campos administrativos no necesarios para el despacho.

### API-007 — Reporte de atenciones

```http
GET /api/v1/reports/attendances?date_from=2026-11-01&date_to=2026-11-30&group_by=hour&user_id=uuid
```

Filtros soportados: fecha, usuario, estado, combustible y agrupación `hour`, `day`, `week` o `month`. El precio/importe deberá calcularse con los snapshots de cada detalle, sujeto a la definición funcional PD-009. No habrá comparación de rangos.

## 14.4. Paginación, filtros y orden

Formato de respuesta:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 0,
    "pages": 0
  }
}
```

Parámetros:

- `page`: mínimo 1, default 1.
- `page_size`: default 20, máximo 100.
- `search`: búsqueda por número o institución, según endpoint.
- `order_number`: número de orden.
- `voucher_number`: número de vale.
- `institution`: nombre de entidad/institución.
- `date_from` / `date_to`: rango inclusivo según fecha de negocio.
- `status`: estado derivado permitido para el recurso.
- `verification_status`: `PENDING`, `VERIFIED` u `OBSERVED` cuando corresponda.
- `sort_by`: enum de columnas permitidas por endpoint.
- `sort_order`: `asc` o `desc`.

Orden predeterminado propuesto: órdenes por fecha de emisión descendente; vales por creación descendente; atenciones por fecha/hora descendente. Órdenes y vales permitirán, como mínimo, fecha y número. La lista final de campos se confirmará con PD-018. Nunca concatenar nombres de columnas no validados en SQL.

## 14.5. Códigos HTTP

| Código | Uso |
|---|---|
| 200 | Consulta, actualización o exportación exitosa. |
| 201 | Recurso creado. |
| 204 | Logout sin cuerpo, si se adopta esa respuesta. |
| 400 | Solicitud mal formada. |
| 401 | No autenticado/token inválido. |
| 403 | Sin permiso o cuenta deshabilitada. |
| 404 | Recurso inexistente o fuera del alcance visible. |
| 409 | Duplicado, saldo insuficiente, conflicto de estado, eliminación bloqueada o idempotency key reutilizada con otro payload. |
| 413 | PDF excede tamaño máximo configurado. |
| 415 | Tipo de archivo no soportado. |
| 422 | Campos o reglas de entrada inválidos. |
| 429 | Límite de solicitudes, si se habilita. |
| 500 | Error inesperado sin información interna. |
| 503 | Base de datos o dependencia crítica no disponible. |

---


# 15. Autenticación, autorización y seguridad

## 15.1. Autenticación

La API requerirá autenticación para todas las operaciones funcionales, salvo health checks. El acceso será mediante correo y contraseña y tokens JWT de vida corta. El backend validará la sesión revocable asociada al identificador `jti`, además del estado activo del usuario.

- Hash de contraseñas con Argon2 mediante `pwdlib`.
- Nunca devolver `password_hash` ni aceptar un hash desde el cliente.
- `POST /api/v1/auth/login`: valida credenciales y cuenta activa; crea sesión y devuelve el token y datos mínimos del usuario, rol, sede y permisos efectivos.
- `POST /api/v1/auth/logout`: revoca la sesión actual.
- `GET /api/v1/auth/me`: devuelve identidad, rol, sede asignada y permisos disponibles.
- Si se deshabilita una cuenta, revocar todas sus sesiones activas.
- No desarrollar recuperación de contraseña hasta que se confirme el procedimiento, pues no se aprobó integración de correo.

El manejo de tokens se documentará junto al frontend. En producción se utilizará HTTPS. La política concreta de almacenamiento/renovación del token debe acordarse con el cliente Angular; no se enviarán credenciales en URL ni se registrarán tokens en logs.

## 15.2. Roles y matriz de autorización

Se implementará RBAC con tres roles predefinidos. El administrador asigna el rol; no se habilita un editor arbitrario de permisos por usuario. El servidor es la autoridad final. La matriz inicial derivada de RF V2 es:

| Funcionalidad | ADMIN | OFFICE | ATTENDANT |
|---|---:|---:|---:|
| Acceder a todos los módulos | Sí | No | No |
| Crear y administrar usuarios/roles | Sí | No | No |
| Habilitar/deshabilitar cuentas | Sí | No | No |
| Consultar órdenes y saldos | Sí | Sí | Sí, para atención |
| Registrar/modificar órdenes | Sí | Sí | No |
| Eliminar orden sin vales asociados | Sí | Sí | No |
| Consultar vales y atenciones | Sí | Sí | Solo los necesarios para atención y sus propios registros |
| Capturar primera atención/vale y atenciones posteriores | Sí, por acceso a todos los módulos | No | Sí, solo las atenciones que realiza |
| Verificar vale físico | Sí | Sí | No |
| Corregir campos descriptivos del vale | Sí | Según matriz final; propuesta inicial: no | No |
| Modificar cantidades de atenciones | No mediante edición directa | No | No |
| Consultar dashboard y reportes | Sí | Sí | No |
| Exportar PDF/XLSX | Sí | Sí | No |
| Ejecutar OCR de órdenes | Sí | Sí | No |

La autorización de ADMIN para registrar una atención no permite alterar movimientos ya confirmados: las atenciones son inmutables. Cada despacho conserva el ID del usuario autenticado que realmente lo ejecutó (`performed_by_user_id`), sea ADMIN o ATTENDANT. La corrección cuantitativa no se habilitará hasta que se apruebe un flujo de ajuste.

Para el rol ATTENDANT, los filtros del servidor limitarán la consulta de atenciones a las propias cuando la consulta no sea necesaria para la atención. El grifero no accederá a datos de precios, importes financieros ni funciones administrativas. La asignación de una sede a cada grifero y la posibilidad de operar desde ambas sedes quedan sujetas a PD-014.

## 15.3. Permisos técnicos

Claves de permisos propuestas para el código (no son roles nuevos):

- `users.manage`
- `purchase_orders.read`, `purchase_orders.create`, `purchase_orders.update`, `purchase_orders.delete`
- `vouchers.read`, `vouchers.verify`, `vouchers.correct_descriptive`
- `attendances.create`, `attendances.read_own`, `attendances.read_all`
- `balances.read`
- `reports.read`, `reports.export`
- `ocr.purchase_orders.process`

La asignación de estas claves se mantendrá en un único módulo de políticas. No duplicar listas de roles en routers distintos. El acceso se comprobará en cada endpoint y en el servicio cuando la regla dependa de propiedad, sede o estado.

## 15.4. Seguridad adicional

- CORS limitado a los orígenes Angular autorizados.
- Validación estricta de requests con Pydantic.
- Consultas parametrizadas mediante SQLAlchemy.
- Límites de tamaño y tiempo para PDF OCR.
- Secretos únicamente mediante variables de entorno.
- No incluir datos de sesión ni tokens en mensajes de error.
- Respuestas 401 para falta de autenticación y 403 para permisos insuficientes.
- No exponer precios/importes a griferos mediante schemas de respuesta alternativos.
- No confiar en el `user_id`, `role`, `branch_id`, `attended_at` o estado enviados por el cliente; esos valores se obtienen de la sesión y de la configuración del servidor.

---

# 16. Servicios y reglas de negocio

Los servicios contienen los casos de uso y coordinan las transacciones. Los routers solo validan el protocolo HTTP, llaman al servicio y convierten resultados en responses. Los repositorios concentran consultas SQLAlchemy y nunca ejecutan `commit`; las entidades ORM se declaran en `app/tables.py`.

## 16.1. Servicios por dominio

| Servicio | Responsabilidad | Operaciones principales |
|---|---|---|
| `AuthService` | Inicio/cierre de sesión y usuario actual. | `login`, `logout`, `get_current_user` |
| `UserService` | Gestión de cuentas y roles fijos. | `create_user`, `list_users`, `set_user_status` |
| `PurchaseOrderService` | Registro, consulta, actualización y eliminación condicionada de órdenes. | `create_order`, `get_order`, `search_orders`, `update_order`, `delete_order` |
| `VoucherService` | Identidad del vale y captura durante primera atención. | `find_existing_voucher`, `create_voucher_with_first_attendance`, `update_descriptive_fields` |
| `AttendanceService` | Registro de cada despacho parcial o completo. | `register_attendance`, `get_attendance`, `list_attendances` |
| `BalanceService` | Cálculo por línea, vale y orden. | `get_order_balances`, `get_voucher_balance`, `calculate_balances` |
| `VoucherVerificationService` | Revisión de vales físicos por Oficina. | `verify_voucher`, `mark_observed`, `get_pending_verifications` |
| `ReportService` | Consultas agregadas para tablas y gráficos. | `get_order_report`, `get_attendance_report`, `get_dashboard_data` |
| `ReportExportService` | Exportación de datasets ya autorizados. | `export_pdf`, `export_xlsx` |
| `PurchaseOrderOcrService` | Extracción temporal de datos de PDF. | `extract_purchase_order_fields` |

## 16.2. Reglas de cantidades

Para cada tipo de combustible se conserva una línea independiente. Los cálculos se realizan con precisión decimal, nunca con `float` binario.

```text
saldo_vale_item = galones_autorizados_vale
                  - SUM(galones_realmente_despachados_en_sus_atenciones)

saldo_orden_item = galones_autorizados_orden
                   - SUM(galones_realmente_despachados_en_todos_los_vales_de_esa_linea)
```

**Regla esencial:** los galones autorizados que aparecen en un vale todavía no atendido no reducen el saldo de la orden. La orden solo disminuye con galones realmente despachados. Esto se ajusta expresamente a RF-020 de la versión 2.0.

Ejemplo de comprobación:

| Evento | Vale autorizado | Entregado ahora | Total entregado | Saldo del vale | Descuento adicional de la orden |
|---|---:|---:|---:|---:|---:|
| Primera atención | 10 | 5 | 5 | 5 | 5 |
| Segunda atención | 10 | 2 | 7 | 3 | 2 |
| Tercera atención | 10 | 3 | 10 | 0 | 3 |

La orden tendrá un descuento acumulado de 10 galones, no de 30. Si una orden contiene Diesel y Gasolina, cada cálculo se ejecuta por su `purchase_order_item_id` y no se compensan saldos entre combustibles.

## 16.3. Primera atención y atenciones siguientes

**Primera atención:** en una única transacción, localizar la orden y línea de combustible, validar la cantidad, crear cabecera del vale, crear las líneas autorizadas del vale, crear la atención y crear sus líneas de galones entregados. Si falla cualquier paso, no se conserva ninguno.

**Atención posterior:** localizar el mismo vale por su identidad de negocio; bloquear la línea de orden y la línea del vale; validar los saldos actuales; registrar una nueva atención y sus detalles. Nunca crear otro vale si coincide con la identidad del vale previamente capturado.

**Despacho completo:** si el despacho actual consume exactamente el saldo restante del vale, el estado derivado queda `COMPLETED`.

**Despacho parcial:** si el despacho es mayor que cero y menor al saldo restante, el estado queda `PARTIALLY_ATTENDED`; el vale puede volver a utilizarse hasta consumir su autorización, siempre que la orden aún tenga saldo.

## 16.4. Verificación de Oficina

La verificación administrativa es independiente del consumo de combustible. Oficina revisa el documento físico contra los datos capturados por el grifero. Si coincide, registra `VERIFIED`; si no coincide, registra `OBSERVED` y una observación. Una verificación jamás cambia galones, atenciones o saldo.

Si se necesita corregir un dato descriptivo, se utilizará la operación autorizada y se conservarán las atenciones. Si el error se encuentra en la cantidad realmente despachada, no se permitirá editar el movimiento original; el procedimiento de ajuste requiere aprobación de PD-006.

## 16.5. Orden, vale y estados derivados

- La orden queda `AVAILABLE` mientras una o más líneas tengan saldo mayor que cero; `DEPLETED` cuando todas las líneas tengan saldo cero.
- Cada línea de orden queda `AVAILABLE` o `DEPLETED` según su propio saldo.
- La línea del vale queda `PENDING` si todavía no tiene atenciones; `PARTIALLY_ATTENDED` si existe consumo y conserva saldo; `COMPLETED` si el saldo llega a cero.
- Si una orden se agota antes que un vale, el vale no se considera completado: permanece con saldo autorizado, pero no puede despacharse hasta que exista saldo de orden. El endpoint debe devolver esta condición explícita, sin saldo negativo ni cambio ficticio a `COMPLETED`.
- El estado de verificación (`PENDING`, `VERIFIED`, `OBSERVED`) es distinto del estado de consumo.
- Los estados no se editan manualmente: se derivan de datos y reglas.

## 16.6. Modificación y eliminación

- Orden: se puede eliminar lógicamente solo si no hay vales asociados. El servidor comprueba dependencias dentro de la transacción y responde `409 ORDER_HAS_VOUCHERS` si existen.
- Orden ya utilizada: no se puede reducir una línea por debajo de los galones que ya se despacharon ni eliminar líneas referenciadas.
- Vale atendido: no se elimina; sus datos descriptivos se corrigen según autorización. Atenciones y sus cantidades son inmutables.
- Usuario: se deshabilita, nunca se elimina físicamente desde la operación normal.
- No se implementan borrados en cascada en datos operativos.

---

# 17. Repositorios, acceso a datos y transacciones

## 17.1. Repositorios

| Repositorio | Responsabilidad |
|---|---|
| `UserRepository` | Crear, consultar, asignar rol fijo y cambiar estado de cuenta. |
| `AuthSessionRepository` | Crear, consultar y revocar sesiones. |
| `BranchRepository` | Consultar sedes preconfiguradas. |
| `FuelTypeRepository` | Consultar tipos de combustible activos. |
| `PurchaseOrderRepository` | Crear, consultar, buscar, paginar, ordenar, actualizar y eliminar lógicamente órdenes. |
| `PurchaseOrderItemRepository` | Consultar y bloquear líneas de orden. |
| `VoucherRepository` | Buscar por identidad de negocio, crear y consultar vales. |
| `VoucherItemRepository` | Consultar y bloquear líneas autorizadas de vales. |
| `AttendanceRepository` | Crear y consultar atenciones y sus líneas; no editar ni borrar movimientos. |
| `VerificationRepository` | Registrar decisiones de verificación y consultar pendientes. |
| `BalanceRepository` | Calcular saldos con agregaciones por línea y combustible. |
| `ReportRepository` | Obtener datos agrupados por intervalo, usuario, estado, sede y combustible. |

No crear un repositorio genérico que oculte consultas de dominio. Los repositorios no ejecutan `commit`; la transacción pertenece al caso de uso/servicio. En el árbol de carpetas, estas clases se implementarán como archivos dentro de `app/repositories/` (por ejemplo, `attendance_repository.py`); los modelos ORM usados por ellas se declaran en `app/tables.py`.

## 17.2. Sesiones y transacciones

- Una sesión SQLAlchemy por request.
- La dependencia FastAPI crea y cierra la sesión.
- El servicio de aplicación define el límite `begin/commit/rollback`.
- Ante cualquier excepción, rollback completo.
- No mantener sesiones abiertas mientras se transmite un archivo OCR o una exportación.

## 17.3. Concurrencia en despachos

Aunque no se anticipen operaciones simultáneas, dos sedes comparten la misma orden; la API debe ser segura ante concurrencia real.

Orden de bloqueos recomendado:

1. Bloquear con `SELECT ... FOR UPDATE` la línea de orden de combustible.
2. Si el vale ya existe, bloquear su línea correspondiente.
3. Calcular los despachos agregados dentro de la transacción.
4. Validar saldo de orden y vale.
5. Insertar la atención y sus líneas.
6. Confirmar.

Todos los flujos deben bloquear las entidades en el mismo orden para minimizar deadlocks. PostgreSQL es la autoridad final; una validación previa enviada por el cliente es informativa y nunca suficiente para autorizar el despacho.

## 17.4. Idempotencia

Las atenciones se enviarán con `Idempotency-Key` UUID generado en el cliente antes del primer intento. El backend persistirá la clave con la operación. Repetir clave y payload idéntico devolverá el resultado existente; repetirla con payload distinto responderá `409 IDEMPOTENCY_KEY_REUSED`. Esta regla protege ante reintentos por conectividad móvil y debe probarse en PostgreSQL.

---

# 18. Validaciones y manejo de errores

## 18.1. Validaciones de dominio

**Usuarios:** nombres y apellidos no vacíos; DNI y correo únicos; correo válido; rol dentro de `ADMIN`, `OFFICE`, `ATTENDANT`; cuenta activa para autenticación; no deshabilitar al último administrador activo.

**Órdenes:** campos obligatorios RF-007; al menos una línea de combustible; tipos activos; cantidades positivas; precios/total no negativos; RUC y número se almacenan como texto; unicidad según política aprobada; no reducir autorizados por debajo de lo ya despachado.

**Vales:** número, emisor y orden válidos; relación de cada línea a una línea de combustible de la misma orden; cantidad autorizada mayor que cero; identidad única según la regla aprobada; múltiples líneas cuando el documento lo permita. Una línea autorizada puede no tener despacho en la primera visita y permanecer `PENDING`. La posibilidad de un mismo número en emisores u órdenes distintos está condicionada a PD-002.

**Atenciones:** cantidad real mayor que cero; referencia a vale/línea válida; cantidad menor o igual al menor saldo entre vale y orden; grifero activo; tipo de combustible coincidente; sede determinada desde el contexto de usuario; no aceptar usuario/fecha/sede manipulados desde el body; clave de idempotencia obligatoria.

**Verificación:** solo Oficina/Admin; decisión `VERIFIED` o `OBSERVED`; observación obligatoria en caso de discrepancia; no alterar datos de consumo.

**OCR:** solo PDF; límite de tamaño/páginas y timeout configurables; limpiar temporales; devolver error manejable ante PDF corrupto, protegido o ilegible.

**Reportes:** agrupaciones permitidas `hour`, `day`, `week`, `month`; rangos válidos; filtros tipados; `page_size` máximo 100 en listados.

## 18.2. Excepciones del dominio

Definir como mínimo: `ResourceNotFoundError`, `DuplicateResourceError`, `InsufficientOrderBalanceError`, `InsufficientVoucherBalanceError`, `OrderHasVouchersError`, `VoucherHasAttendancesError`, `InvalidFuelLineError`, `InactiveUserError`, `LastActiveAdminError`, `IdempotencyConflictError`, `VoucherIdentityConflictError`, `InvalidVerificationTransitionError` y `OcrProcessingError`.

## 18.3. Respuesta estándar

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "El saldo disponible no permite completar el despacho.",
    "details": {
      "order_item_balance": "70.000",
      "voucher_item_balance": "5.000"
    }
  }
}
```

Mapeo: `401` no autenticado; `403` permiso insuficiente; `404` recurso no encontrado; `409` saldo insuficiente, duplicado, conflicto de idempotencia, eliminación bloqueada o estado incompatible; `413` archivo excede el tamaño; `415` formato no permitido; `422` validación de entrada; `500` error inesperado; `503` servicio crítico no disponible.

No devolver stack traces, SQL, rutas internas, hash de contraseña, token ni datos sensibles.

---

# 19. Procesamiento de archivos y OCR

## 19.1. Alcance exacto

RF-034 contempla exclusivamente PDF de órdenes de compra para extraer los campos que completan el formulario de registro. No se procesarán vales, fotografías de vales, imágenes sueltas, facturas ni otros documentos en esta versión.

## 19.2. Flujo de OCR

1. Usuario autorizado de Oficina/Admin carga el PDF.
2. Backend valida extensión, MIME real, firma, tamaño, número de páginas y protección del archivo.
3. El archivo se almacena en un directorio temporal fuera del directorio público.
4. Se extrae texto embebido si está disponible; para páginas escaneadas, PyMuPDF renderiza páginas y RapidOCR realiza reconocimiento.
5. El servicio construye candidatos para cabecera y líneas de combustible: número, SIAF, fecha, proveedor, unidad ejecutora, RUC, combustible, cantidad, precio unitario y total, cuando se detecten.
6. La API devuelve los datos extraídos y, cuando la librería lo exponga de forma fiable, indicadores de confianza por campo.
7. El frontend presenta el formulario prellenado; el usuario revisa y corrige los campos.
8. El guardado se realiza mediante el endpoint normal de órdenes, solo después de confirmación humana.
9. Se eliminan los temporales al finalizar, tanto en éxito como en error.

OCR no crea órdenes, no genera saldos y no sustituye las validaciones de negocio. Si no se reconoce un campo, el usuario lo completa manualmente. Si OCR falla, se permite continuar con registro manual.

## 19.3. Dependencias y controles

- RapidOCR y su runtime compatible fijados en los archivos de dependencias del proyecto.
- PyMuPDF para lectura/renderizado de páginas.
- `python-multipart` para carga `multipart/form-data`.
- Directorio temporal configurable, con permisos restrictivos.
- Timeout y límites configurables; valores concretos aprobados mediante PD-012.
- No registrar ni persistir contenido PDF, texto completo extraído ni datos personales no necesarios.
- Pruebas con muestras reales anonimizadas de órdenes de ambas sedes.

No utilizar Tesseract como motor alternativo en esta versión; mantener un único motor evita discrepancias de extracción y dependencias innecesarias.

---

# 20. Reportes, dashboard y exportación

## 20.1. Reportes incluidos

- Reporte de órdenes de compra: entidad, número, fecha, unidad ejecutora, combustible, cantidades autorizadas, realmente despachadas y saldo por tipo.
- Reporte de atenciones: número de vale, orden, institución, combustible, galones entregados en esa atención, fecha/hora, grifero y sede.
- Datos de dashboard con agrupación por hora, día, semana y mes.
- Filtros por fechas, usuarios y estados. Los filtros adicionales de combustible/sede pueden utilizarse como desglose técnico si se aprueban y no contradicen permisos.

El precio unitario snapshot y los importes atendidos solo se expondrán a Admin/Oficina, sujetos a PD-009. No enviar esos campos a Grifero.

## 20.2. Dashboard

El `DashboardService` devolverá series agregadas y totales que alimentan gráficos interactivos. No incluirá indicadores de rendimiento ni comparación de períodos, porque la RF V2 eliminó comparación y señaló que no se requieren KPI. La selección exacta de gráficos e indicadores queda sujeta a PD-010.

## 20.3. Exportación

- PDF con ReportLab.
- XLSX con openpyxl.
- La exportación reutiliza los mismos filtros, permisos y dataset del reporte consultado.
- Respetar la paginación/alcance solicitado y limitar exportaciones excesivas.
- Los archivos se devuelven como descarga HTTP y no se almacenan permanentemente salvo requerimiento posterior.

No desarrollar endpoint de impresión ni comparación de períodos. La impresión directa no forma parte de RF V2.

---

# 21. Migraciones y datos iniciales

## 21.1. Alembic

Alembic será la única vía versionada para crear y modificar el esquema. La migración inicial debe incluir, en orden de dependencia: `branches`, `users`, `auth_sessions`, `fuel_types`, `purchase_orders`, `purchase_order_items`, `vouchers`, `voucher_items`, `attendances`, `attendance_items`, `attendance_verifications` y la tabla de idempotencia si no se resuelve en `attendances`.

Las restricciones únicas y FK deben corresponder al ER aprobado. No permitir cascadas de eliminación en relaciones que contienen consumo o historial.

## 21.2. Seeds

- Sedes San José y Santa Marta.
- Catálogo de tipos de combustible confirmado por la estación.
- Cuenta Admin inicial creada por comando/secretos de entorno de instalación.
- Roles como enum fijo de aplicación; no crear catálogo editable de roles.
- Seeds idempotentes; no sobrescribir usuarios ni credenciales preexistentes.

## 21.3. Datos históricos

No importar Excel/PDF existentes ni realizar migración histórica en esta versión, según el alcance confirmado. Los reportes incluirán los registros creados en el sistema desde su puesta en producción.

---

# 22. Configuración y variables de entorno

## 22.1. Ambientes

- `development`: desarrollo local.
- `testing`: PostgreSQL aislado de pruebas.
- `production`: despliegue real.

## 22.2. `.env.example`

```env
APP_NAME="San Jose Fuel Control API"
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
TIMEZONE=America/Lima

DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/san_jose_db

JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_ISSUER=san-jose-api

CORS_ORIGINS=http://localhost:4200
LOG_LEVEL=INFO

OCR_ENABLED=true
OCR_MAX_UPLOAD_BYTES=10485760
OCR_MAX_PDF_PAGES=20
OCR_TIMEOUT_SECONDS=60
OCR_TEMP_DIR=/tmp/san-jose-ocr
```

Los límites OCR son valores iniciales propuestos y deben aprobarse con PD-012. No codificar claves reales en el repositorio. Validar configuración al arranque, usar `DEBUG=false` en producción y restringir CORS a dominios conocidos.

---

# 23. Documentación OpenAPI y contrato con Angular

FastAPI será la fuente del contrato OpenAPI una vez implementados los endpoints. Título: `San José Fuel Control API`; versión inicial de API: `1.0.0`; prefijo `/api/v1`.

Tags: `Auth`, `Users`, `Branches`, `Catalogs`, `Purchase Orders`, `Vouchers`, `Attendances`, `Balances`, `Verifications`, `Reports`, `OCR` y `Health`.

Cada operación documentará roles autorizados, request/response schemas, filtros, paginación, códigos de error y ejemplos sin datos reales. El frontend Angular podrá generar o sincronizar clientes a partir del OpenAPI real; los archivos generados no se editarán manualmente.

El contrato se considera **planificado** hasta que exista implementación, OpenAPI generado y pruebas de integración. Cualquier discrepancia entre RF, el plan y OpenAPI debe corregirse antes de cerrar la fase correspondiente.

---

# 24. Pruebas y calidad

## 24.1. Niveles

1. **Unitarias:** fórmulas de saldo, estados derivados, validaciones, reglas de acceso y servicios.
2. **Integración:** repositorios, FK, unicidad, transacciones, `SELECT FOR UPDATE` e idempotencia en PostgreSQL.
3. **API:** métodos HTTP, schemas, roles, respuestas, filtros, paginación y exportación.
4. **End-to-end backend:** flujos completos de primera atención, atención posterior, verificación y reportes.

## 24.2. Casos de prueba críticos de saldo

| ID | Escenario | Resultado esperado |
|---|---|---|
| TC-001 | Línea de orden: 100 galones; vale nuevo autoriza 10; grifero entrega 5. | Se crea vale y atención; saldo del vale 5; saldo de orden 95. |
| TC-002 | Mismo vale: quedan 5; nueva atención entrega 2. | Nueva atención; vale 3 restantes; orden descuenta 2 adicionales. |
| TC-003 | Mismo vale: quedan 3; última atención entrega 3. | Vale `COMPLETED`; saldo del vale 0; orden descuenta 3. |
| TC-004 | Vale nuevo autoriza 10, pero no ha tenido despacho. | La orden no descuenta esos 10 autorizados. |
| TC-005 | Un despacho supera el saldo restante del vale. | `409`; no se inserta atención ni se altera saldo. |
| TC-006 | El saldo de orden es menor que el despacho solicitado. | `409`; no se inserta atención ni se altera saldo. |
| TC-007 | Orden con Diesel y Gasolina. | Despacho Diesel solo descuenta línea Diesel; Gasolina permanece igual. |
| TC-008 | Vale con varias líneas de combustible. | Cada línea conserva autorización, despachado y saldo independiente. |
| TC-009 | La orden se agota mientras el vale conserva saldo. | Vale muestra saldo pendiente bloqueado por falta de saldo de orden; no se marca completado. |
| TC-010 | Dos sedes despachan simultáneamente sobre la misma línea. | Bloqueo/transacción impide consumo acumulado mayor a saldo disponible. |
| TC-011 | El cliente reintenta el mismo POST por pérdida de respuesta. | Idempotencia devuelve la atención original, sin doble descuento. |
| TC-012 | Oficina verifica un vale. | Cambia estado de verificación; no cambia ninguna cantidad ni saldo. |
| TC-013 | Oficina marca el vale observado. | Permanece pendiente/observado, con observación; saldo intacto. |
| TC-014 | Intento de editar cantidad real de una atención. | Rechazado; movimiento original inmutable. |
| TC-015 | Eliminar orden con vale vinculado. | `409 ORDER_HAS_VOUCHERS`; no borra ninguna entidad relacionada. |
| TC-016 | Eliminar vale que tiene atenciones. | `409`; se conserva vale e historial. |
| TC-017 | Deshabilitar usuario con atenciones previas. | Cuenta sin acceso; las atenciones conservan la identidad del autor. |
| TC-018 | Usuario ATTENDANT solicita reportes financieros. | `403`. |
| TC-019 | OCR PDF legible. | Devuelve campos candidatos; no crea orden. |
| TC-020 | OCR PDF corrupto/ilegible. | Error controlado; temporal eliminado; formulario manual disponible. |

## 24.3. Pruebas por rol

- **ADMIN:** gestión de usuarios; acceso a todos los módulos; consulta y supervisión; reportes/exportaciones; operaciones administrativas autorizadas. No edita directamente atenciones.
- **OFFICE:** gestión de órdenes; consulta y verificación de vales; reportes/exportaciones; OCR. No registra despachos como grifero.
- **ATTENDANT:** buscar órdenes, consultar saldos, capturar vales en primera atención, registrar atenciones parciales posteriores y consultar su resultado. No gestionar órdenes, verificar vales, administrar usuarios ni acceder a reportes financieros.

## 24.4. Calidad

Objetivos propuestos: cobertura mínima de 85% en servicios de dominio; 100% de cobertura de casos críticos de saldo, idempotencia y autorización. Ruff sin errores. Mypy sin errores en módulos críticos o excepciones justificadas. Ejecutar pruebas de concurrencia en PostgreSQL, no solo SQLite. Ninguna prueba accede a datos de producción.

---

# 25. Logging, trazabilidad y monitoreo

## 25.1. Logging técnico

Registrar errores no controlados, latencia y código HTTP, fallos de conexión, fallos OCR/exportación y accesos denegados. No registrar contraseñas, hashes, JWT, PDF completos, texto OCR completo ni datos personales innecesarios. Incluir `request_id` para correlacionar cada petición.

## 25.2. Trazabilidad funcional

La trazabilidad necesaria de los despachos estará en `attendances` y `attendance_items`: vale, cantidad efectivamente despachada, usuario autenticado que ejecutó la operación, sede, fecha/hora y tipo de combustible. Las verificaciones se conservan en `attendance_verifications` con usuario revisor, resultado, observación y fecha/hora.

No se implementará auditoría general de todas las acciones de usuario, pues no está contemplada por RF V2. La inmutabilidad de atenciones y el historial de verificaciones sí son necesarios para el flujo descrito.

## 25.3. Health checks

- `GET /health/live`: indica que el proceso está activo.
- `GET /health/ready`: verifica dependencias críticas, incluyendo PostgreSQL.
- Los health checks no deben exponer credenciales, rutas internas o topología sensible.

---

# 26. Rendimiento, integridad y escalabilidad

## 26.1. Desde el inicio

- Paginación en órdenes, vales, atenciones y bandeja de verificación.
- Índices en claves foráneas, números documentales, fechas, entidad y estados.
- Consultas agregadas para saldos, sin recorrer registros en Python.
- Bloqueos transaccionales para las líneas implicadas en cada atención.
- Prevención de N+1 y selección de columnas necesarias en listados.
- `EXPLAIN ANALYZE` con conjuntos representativos en consultas de reportes.
- Tamaño de página máximo propuesto: 100.
- Exportaciones limitadas y generadas a partir de consultas con filtros; streaming cuando el volumen lo justifique.

## 26.2. Índices sugeridos

- `users(email)` UNIQUE; `users(dni)` UNIQUE; `users(branch_id)`.
- `purchase_orders(executing_unit_ruc, order_number)` UNIQUE según PD-001.
- `purchase_orders(institution_name)` para búsquedas normalizadas; `purchase_orders(issue_date)`.
- `purchase_order_items(purchase_order_id, fuel_type_id)` con unicidad de combustible por orden si el modelo funcional lo confirma.
- `vouchers(purchase_order_id, issuer_type, issuer_id, normalized_voucher_number)` UNIQUE según PD-002.
- `voucher_items(voucher_id, purchase_order_item_id)`.
- `attendances(voucher_id, attended_at)`; `attendances(performed_by_user_id, attended_at)`; `attendances(branch_id, attended_at)`.
- `attendance_items(attendance_id, voucher_item_id)`.
- `attendance_verifications(attendance_id, verified_at)`.
- `auth_sessions(jti)` UNIQUE y `auth_sessions(user_id, expires_at)`.

Las restricciones de unicidad definitivas se fijarán después de validar si los vales pueden reutilizar un número por emisor, orden o institución.

## 26.3. Posponer hasta tener métricas

No incorporar Redis, Celery, Kafka, caché distribuida, réplicas de lectura, particionamiento de atenciones ni colas de exportación en esta versión. Evaluarlos solo si métricas de producción muestran necesidad.

---

# 27. Plan de implementación por fases

## F0 — Cierre de decisiones funcionales y diseño

**Objetivo:** aprobar decisiones que afectan integridad, cantidades y captura de vales.  
**Dependencias:** ninguna.  
**RF:** todos; foco en RF-007, RF-013–RF-019, RF-020–RF-026 y RF-034.  
**Módulos:** todos.

**Tareas:** aprobar identidad única de orden/vale; catálogo de combustible; asociación de vale a una o varias líneas; reglas de cantidad decimal; política de despacho parcial; sede del usuario; verificación y manejo de observaciones; corrección de despachos erróneos; datos confidenciales; límites OCR; columnas de reportes; zona horaria y redondeos.

**Entregables:** ADR aprobados, ER lógico y matriz de permisos.  
**Pruebas:** escenarios de aceptación firmados, incluyendo 10/5, 10/10 y múltiples combustibles.  
**Gate:** no iniciar F5 sin aprobar numeración, línea de combustible, política de despacho parcial e idempotencia; PD-006 debe resolverse antes de habilitar correcciones de cantidades.

## F1 — Fundaciones de FastAPI y calidad

**Objetivo:** aplicación ejecutable con configuración, DB, logging y pruebas.  
**Dependencias:** F0.  
**RF:** transversal.  
**Tareas:** crear entorno Python; configurar FastAPI/Uvicorn, Pydantic Settings, SQLAlchemy, PostgreSQL, Alembic, routers `/api/v1`, excepciones, logging, Ruff, Mypy, Pytest, HTTPX y Docker Compose; implementar health checks.  
**Pruebas:** arranque, conexión DB, configuración inválida y health checks.  
**Gate:** app inicia y falla de forma controlada cuando PostgreSQL no está disponible.

## F2 — Modelo de datos, migraciones y catálogos

**Objetivo:** persistencia normalizada con restricciones.  
**Dependencias:** F1 y decisiones de F0.  
**RF:** RF-001, RF-007, RF-013–RF-026.  
**Tablas:** sedes, usuarios, sesiones, combustibles, órdenes, líneas, vales, líneas de vale, atenciones, líneas de atención y verificaciones.  
**Tareas:** modelos ORM; relaciones; checks; índices; `ON DELETE RESTRICT`; migración inicial; seeds de sedes y combustibles; creación segura de Admin.  
**Pruebas:** migración desde DB vacía, FK, unicidad, integridad de líneas y seeds idempotentes.  
**Gate:** DB construida únicamente con Alembic y modelo probado en PostgreSQL.

## F3 — Autenticación, usuarios y RBAC

**Objetivo:** acceso seguro para ADMIN, OFFICE y ATTENDANT.  
**Dependencias:** F2.  
**RF:** RF-001–RF-006.  
**Endpoints:** `/auth/login`, `/auth/logout`, `/auth/me`, `/users`, `/users/{id}`, habilitar/deshabilitar cuenta.  
**Tareas:** hashing Argon2; tokens; sesiones revocables; políticas por rol; schemas de usuario; deshabilitación y revocación; prohibir deshabilitar último Admin.  
**Pruebas:** acceso permitido/denegado por rol, token revocado, cuenta inactiva y conservación de registros históricos.  
**Gate:** no es posible operar sin autenticación ni ejecutar acciones fuera del rol.

## F4 — Órdenes de compra y líneas por combustible

**Objetivo:** registrar, consultar, filtrar, ordenar, modificar y eliminar condicionalmente órdenes.  
**Dependencias:** F3 y catálogos de F2.  
**RF:** RF-007–RF-012, RF-032.  
**Endpoints:** `/purchase-orders`, `/purchase-orders/{id}`, `/purchase-orders/{id}/balances`, catálogos de combustible.  
**Tareas:** schemas de cabecera y líneas; registro multi-combustible; detalle; búsqueda por número/entidad; filtros; paginación; sort allowlist; actualización protegida por galones ya despachados; eliminación solo sin vales.  
**Pruebas:** múltiples líneas, datos obligatorios, duplicados, bloqueo de eliminación y reducción de cantidades.  
**Gate:** orden y líneas consistentes; saldos de línea calculables antes de habilitar atenciones.

## F5 — Captura de vales y despachos parciales

**Objetivo:** capturar un vale en el primer despacho y permitir múltiples atenciones parciales posteriores, sin pre-registro por Oficina.  
**Dependencias:** F4 y permisos de F3.  
**RF:** RF-014–RF-026.  
**Endpoints:** búsqueda de órdenes; `POST /attendances`; `GET /vouchers`; `GET /vouchers/{id}`; consultas de balances.  
**Tareas:** identidad única de vale; captura de cabecera/líneas al primer despacho; atención inicial atómica; atención posterior sobre saldo; múltiples combustibles; cálculo por línea; transacciones y `SELECT FOR UPDATE`; idempotencia; estados derivados; sede y usuario desde sesión.  
**Pruebas:** TC-001 a TC-011; concurrencia entre sedes; reintentos móviles; consumo parcial y completo.  
**Gate:** ninguna operación puede generar saldo negativo ni duplicar una atención; verificación integral con ejemplos 10/5, 10/2, 10/3 y entrega 10/10.

## F6 — Bandeja y verificación de Oficina

**Objetivo:** permitir la revisión del vale físico sin volver a registrar el documento.  
**Dependencias:** F5.  
**RF:** RF-013, RF-017, RF-018.  
**Endpoints:** `GET /verifications/pending`, `POST /attendances/{id}/verifications`, `GET /vouchers/{id}` y corrección descriptiva autorizada.  
**Tareas:** bandeja pendiente; detalle completo; resultado VERIFIED/OBSERVED; observación obligatoria si no coincide; registro del revisor/fecha; protección de movimientos; corrección de datos descriptivos; impedir eliminación de vales atendidos.  
**Pruebas:** verificación coincidente, observación, segunda revisión y asegurar que ninguna cambia los saldos.  
**Gate:** verificación no crea otro vale ni modifica consumo.

## F7 — Reportes, dashboard y exportación

**Objetivo:** consulta gerencial y operativa de órdenes y atenciones.  
**Dependencias:** F5; F6 para filtros de verificación si son solicitados.  
**RF:** RF-027–RF-031.  
**Endpoints:** `/reports/purchase-orders`, `/reports/attendances`, `/reports/dashboard`, exportación PDF/XLSX.  
**Tareas:** queries agregadas; agrupación por hora/día/semana/mes; filtros por fecha/usuario/estado; dataset por combustible; gráficos; ReportLab/openpyxl; restricciones de datos sensibles según rol.  
**Pruebas:** agregaciones; rangos temporales; timezone; no comparar períodos; no imprimir; exportar con mismos filtros del reporte.  
**Gate:** reportes coinciden con registros reales y no exponen importes a Grifero.

## F8 — OCR de órdenes con RapidOCR

**Objetivo:** prellenar el formulario de orden desde PDF, sin guardar automáticamente.  
**Dependencias:** F4 y F0 para límites OCR.  
**RF:** RF-007, RF-034.  
**Endpoints:** `POST /ocr/purchase-order-previews`.  
**Tareas:** upload temporal; detección MIME; extracción texto PDF; renderizado PyMuPDF; RapidOCR; normalización de campos; resultado parcial con campos no reconocidos; borrado de temporales; manual fallback; revisión humana.  
**Pruebas:** PDF legible, escaneado, corrupto, protegido, grande, multi página y OCR parcial.  
**Gate:** no se crea una orden hasta que Oficina/Admin confirme el formulario normal.

## F9 — Endurecimiento, documentación y producción

**Objetivo:** estabilizar, documentar y preparar despliegue.  
**Dependencias:** F1–F8 según alcance habilitado.  
**RF:** todos.  
**Tareas:** pruebas E2E de flujos; pruebas simultáneas; permisos por endpoint; límites OCR/exportación; revisión de logs; migraciones desde una copia reciente; backups; HTTPS; CORS de producción; documentación OpenAPI; guía de operación; prueba de restauración.  
**Gate:** todos los RF habilitados tienen evidencia de pruebas, no existen fallos críticos y el despliegue puede reproducirse.

---

# 28. Matriz de trazabilidad RF → backend

La matriz resume el componente backend principal. Los endpoints son **propuestos** para el contrato `/api/v1`; no se consideran implementados hasta existir código y OpenAPI verificado.

| RF | Funcionalidad | Módulo/servicio | Endpoint(s) principal(es) | Fase |
|---|---|---|---|---|
| RF-001 | Registrar usuario | users / `UserService` | `POST /users` | F3 |
| RF-002 | Roles y permisos predefinidos | core/auth | `GET /auth/me` | F3 |
| RF-003 | Iniciar sesión | auth / `AuthService` | `POST /auth/login` | F3 |
| RF-004 | Habilitar/deshabilitar usuario | users | `PATCH /users/{id}/status` | F3 |
| RF-005 | Cerrar sesión | auth | `POST /auth/logout` | F3 |
| RF-006 | Consultar atenciones de griferos (Admin) | attendances | `GET /attendances` | F5 |
| RF-007 | Registrar orden | purchase_orders | `POST /purchase-orders` | F4 |
| RF-008 | Detalle de orden | purchase_orders | `GET /purchase-orders/{id}` | F4 |
| RF-009 | Buscar orden | purchase_orders | `GET /purchase-orders` | F4 |
| RF-010 | Paginar órdenes | purchase_orders | `GET /purchase-orders?page=&page_size=` | F4 |
| RF-011 | Modificar orden | purchase_orders | `PATCH /purchase-orders/{id}` | F4 |
| RF-012 | Eliminar orden sin vales | purchase_orders | `DELETE /purchase-orders/{id}` | F4 |
| RF-013 | Verificar vale físico | verification | `POST /attendances/{id}/verifications` | F6 |
| RF-014 | Consultar orden/saldo y vale previo | balances/vouchers | `GET /purchase-orders`, `GET /vouchers/{id}/balance` | F4–F5 |
| RF-015 | Buscar órdenes/vales por número o entidad | purchase_orders/vouchers | `GET /purchase-orders`, `GET /vouchers` | F4–F5 |
| RF-016 | Paginar vales | vouchers | `GET /vouchers?page=&page_size=` | F5 |
| RF-017 | Corregir datos descriptivos del vale | vouchers | `PATCH /vouchers/{id}/descriptive-data` | F6 |
| RF-018 | Impedir eliminar vales atendidos | vouchers | `DELETE /vouchers/{id}` (rechazo `409` si hay atenciones) | F5 |
| RF-019 | Capturar vale + primera atención y atenciones posteriores | attendances/vouchers | `POST /attendances` | F5 |
| RF-020 | Calcular saldo de orden por combustible | balances | `GET /purchase-orders/{id}/balances` | F5 |
| RF-021 | Calcular saldo restante del vale | balances | `GET /vouchers/{id}/balance` | F5 |
| RF-022 | Validar saldos antes del despacho | `AttendanceService` | dentro de `POST /attendances` | F5 |
| RF-023 | Actualizar saldos atómicamente | `AttendanceService` | dentro de `POST /attendances` | F5 |
| RF-024 | Consultar órdenes y saldos | balances | `GET /purchase-orders`, `/balances` | F4–F5 |
| RF-025 | Compartir saldos entre sedes | branches/balances | los mismos endpoints con DB central | F4–F5 |
| RF-026 | Estados automáticos | balances/domain | incluidos en responses de órdenes/vales | F5 |
| RF-027 | Reportes de órdenes | reports | `GET /reports/purchase-orders` | F7 |
| RF-028 | Reportes de vales atendidos | reports | `GET /reports/attendances` | F7 |
| RF-029 | Filtros de reportes | reports | query parameters de reportes | F7 |
| RF-030 | Dashboard con gráficos | reports | `GET /reports/dashboard` | F7 |
| RF-031 | Exportar PDF/XLSX | reports/exporters | `GET /reports/purchase-orders/export` y `GET /reports/attendances/export` con `format=pdf` o `format=xlsx` | F7 |
| RF-032 | Ordenar órdenes | purchase_orders | `sort_by`, `sort_order` en listado | F4 |
| RF-033 | Ordenar vales | vouchers | `sort_by`, `sort_order` en listado | F5 |
| RF-034 | OCR RapidOCR para PDF de órdenes | ocr | `POST /ocr/purchase-order-previews` | F8 |

**Control de cambios:** RF V2 contiene 34 RF. No debe aparecer una ruta/servicio para comparación de períodos ni impresión de reportes. Si un número cambia en una siguiente versión del RF, actualizar esta matriz y los tests de trazabilidad.

---

# 29. Riesgos, supuestos y decisiones pendientes

## 29.1. Decisiones resueltas para planificar

| Tema anterior | Decisión actual | Justificación |
|---|---|---|
| Vale pre-registrado por Oficina | Se crea junto con el primer despacho del grifero. | Flujo operativo RF V2. |
| Una atención por vale | Se permiten múltiples atenciones parciales. | RF-019 y ejemplo 10/5. |
| Una sola cantidad de vale | Se modelan líneas por tipo de combustible. | Evita mezclar saldos de combustibles diferentes. |
| Descontar vale autorizado de orden | La orden descuenta solo galones realmente despachados. | RF-020. |
| Oficina vuelve a registrar vale | Oficina solo verifica el registro capturado. | RF-013. |
| Tesseract / OCR genérico | RapidOCR solo para PDF de órdenes. | RF-034. |
| Borrado físico de usuarios | Deshabilitar cuentas y revocar sesiones. | RF-004 y conservación histórica. |
| Borrado de orden con dependencias | Bloquear si tiene vales. | RF-012. |
| Comparar períodos / imprimir | Fuera del alcance. | Eliminado de RF V2. |

## 29.2. Pendientes funcionales/decisiones técnicas

| ID | Tema | Decisión necesaria | Impacto | Bloquea |
|---|---|---|---|---|
| PD-001 | Identidad única de órdenes | Confirmar si número de orden es único por RUC/unidad ejecutora o por institución y qué campo identifica institución. | Restricción única y búsquedas. | F4 |
| PD-002 | Identidad y emisor de vales | Confirmar numeración de vales por emisor, entidad y orden; si el número puede repetirse entre documentos. | Dedupe/índice único. | F5 |
| PD-003 | Datos de proveedor | Confirmar campos estructurados de proveedor y sedes/proveedor legal. | Schema de orden y OCR. | F4/F8 |
| PD-004 | Varias líneas por vale | Confirmar si el vale físico puede incluir más de un combustible y si siempre se puede asociar cada línea a la línea de orden correspondiente. | `voucher_items`, `attendance_items`. | F5 |
| PD-005 | Estado cuando orden agotada y vale conserva saldo | Aprobar presentación: vale con saldo restante pero no despachable por saldo de orden agotado. | Estado y UI. | F5 |
| PD-006 | Error en galones ya despachados | Definir quién autoriza el ajuste, motivo obligatorio, efecto en saldos y registro de reversión compensatoria. | Modelo de ajustes/inmutabilidad. | Correcciones cuantitativas; no bloquea el flujo base |
| PD-007 | Contraseñas | Definir cambio de contraseña inicial y restablecimiento administrativo sin correo. | Endpoints/auth. | F3 completo |
| PD-008 | Cierre remoto | Confirmar si Admin puede revocar sesiones de otros usuarios o solo cada usuario la propia. | Sesiones y endpoint administrativo. | Complemento F3 |
| PD-009 | Precios en reportes | Confirmar qué importes/precios se muestran, incluidos los snapshots y el acceso confidencial. | Schemas/reportes. | F7 completo |
| PD-010 | Gráficos | Confirmar tipos de gráficos y agregaciones exactas. | Dashboard. | F7 completo |
| PD-011 | Vale observado | Definir proceso cuando Oficina detecta discrepancia y quién puede resolverla; por ahora no altera despachos ni saldo. | Verificación y corrección. | Cierre F6 |
| PD-012 | Restricciones PDF | Aprobar tamaño máximo, número de páginas y timeout. | OCR/seguridad. | F8 |
| PD-013 | Datos confidenciales | Precisar campos confidenciales y reglas de acceso por rol. | Schemas y filtros. | Seguridad de F7 |
| PD-014 | Sede del grifero | Confirmar si cada grifero pertenece a una sede fija o puede operar en ambas. | `users.branch_id`, `attendances.branch_id`. | F3/F5 |
| PD-015 | Cantidad de usuarios | Resolver diferencia entre 6 trabajadores y estimado 8 cuentas. | Planificación de capacidad, no esquema. | No bloquea |
| PD-016 | Datos históricos | Confirmar que archivos históricos permanecerán fuera del sistema y no se cargarán. | Alcance de informes. | No bloquea; decisión actual: no migrar |
| PD-017 | Consulta fuera de horario | Confirmar disponibilidad de consulta fuera del horario de trabajo. | RNF/operación. | Despliegue final |
| PD-018 | Campos de ordenación | Aprobar campos y orden ascendente/descendente. | Allowlist sort. | F4/F5 completo |
| PD-019 | Zona horaria | Confirmar `America/Lima` como zona de negocio. | Agrupación temporal/reportes. | F7 |
| PD-020 | Precisión/redondeo | Aprobar decimales de galones, precio unitario y montos; propuesta: 3, 4 y 2 decimales. | NUMERIC y cálculo. | F0/F2 |

## 29.3. Supuestos técnicos explícitos

- PostgreSQL centralizado será utilizado por ambas sedes; no habrá bases separadas que se sincronicen.
- Cada vale nuevo se captura con al menos un primer despacho dentro de una única transacción.
- Los galones se ingresan como decimal; la precisión exacta debe aprobarse.
- La fecha/hora de atención será generada por servidor y almacenada como `TIMESTAMPTZ` en UTC.
- El frontend puede reintentar operaciones con clave de idempotencia.
- Los documentos enviados a OCR se procesan temporalmente y no permanecen almacenados.

Estos supuestos técnicos no se deben presentar como decisiones de negocio aprobadas hasta que los responsables los confirmen.

---

# 30. Definition of Done general

Una fase estará terminada solo cuando:

1. Los cambios corresponden a RF V2 y a decisiones aprobadas.
2. Cada endpoint tiene autenticación, autorización y schemas documentados.
3. La lógica de negocio está en servicios, no en routers.
4. Las cantidades usan `Decimal`/`NUMERIC`, nunca `float`.
5. Los saldos se derivan de cantidades autorizadas y atenciones efectivas; no se aceptan del cliente.
6. Las atenciones se registran de forma atómica, con locks e idempotencia.
7. Las líneas de combustibles no comparten ni compensan saldos.
8. La verificación administrativa no modifica consumo.
9. Las dependencias protegen el historial y no hay cascadas destructivas.
10. Las migraciones Alembic están versionadas y probadas.
11. Las pruebas unitarias, integración y API relevantes pasan.
12. Ruff y Mypy cumplen las reglas configuradas.
13. No existen secretos ni datos sensibles en logs/repositorio.
14. OpenAPI refleja las rutas reales.
15. Se documentan decisiones y pendientes que bloquean el alcance.
16. No se marca como implementado aquello que solo está planificado.

---

# 31. Orden recomendado de desarrollo

1. Aprobar decisiones F0 que afectan identidad, cantidades, combustibles, sedes y precisión.
2. Construir el esqueleto y base de datos.
3. Implementar autenticación y RBAC antes de exponer operaciones.
4. Implementar órdenes con múltiples líneas de combustible.
5. Implementar búsqueda de orden y consulta de saldo.
6. Implementar captura del vale y su primera atención en una sola transacción.
7. Implementar las atenciones parciales siguientes y el cálculo independiente de saldo por vale/línea/orden.
8. Implementar idempotencia y pruebas de concurrencia entre sedes.
9. Implementar bandeja de verificación de Oficina y corrección descriptiva.
10. Implementar reportes/dashboard y exportación PDF/XLSX.
11. Implementar RapidOCR para PDF de órdenes, manteniendo revisión humana.
12. Ejecutar pruebas integrales, seguridad, documentación y despliegue.

No habilitar la captura real de atenciones hasta que se hayan probado los escenarios parciales/completos, multi combustible, concurrencia y reintentos.

---

# 32. Cierre del plan

La versión actualizada del backend debe reflejar el proceso real de la Estación de Servicio San José: la orden es registrada por Oficina; el cliente presenta su vale físico; el grifero consulta la orden y captura el vale junto con el despacho inicial; el mismo vale puede recibir una o varias atenciones parciales; cada atención descuenta exclusivamente los galones realmente entregados del saldo de su vale y de la línea correspondiente de la orden; y Oficina verifica después el documento físico sin duplicar el registro ni alterar el consumo.

La separación entre `vouchers`, `voucher_items`, `attendances` y `attendance_items` es la decisión estructural clave para representar este flujo correctamente. La API debe proteger esta lógica en transacciones PostgreSQL, con permisos de servidor, idempotencia y pruebas de concurrencia.

La versión 2.1 conserva las decisiones funcionales de la versión 2.0 y actualiza la organización del código a una arquitectura por capas. Reemplaza la estructura de directorios anterior basada en `app/modules/`. Las propuestas técnicas y pendientes identificados deben revisarse antes de liberar los módulos correspondientes. Los endpoints, modelos y fases aquí descritos son una especificación de implementación, no evidencia de que el backend esté desarrollado.

**Fin del documento.**

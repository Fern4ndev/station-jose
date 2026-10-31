# Especificación de Requerimientos Funcionales del Sistema

**Sistema:** Sistema web con OCR para la gestión de combustible institucional, estación de servicio San José, Abancay
**Tipo de aplicación:** frontend Angular 21.2.0, API FastAPI y PostgreSQL, con lectura de documentos por RapidOCR
**Versión:** 3.0
**Fecha:** octubre de 2026
**Reemplaza a:** `requerimientos-funcionales.md` (v1.1). Esta versión describe únicamente el sistema: se retiraron los módulos de encuesta y de medición del estudio, que pertenecen a la tesis y no al sistema.

<a id="indice"></a>

## Índice

1. [Introducción](#intro)
   - [1.1 Propósito](#intro-proposito)
   - [1.2 Convenciones del documento](#intro-convenciones)
2. [Alcance](#alcance)
   - [2.1 Objetivo del sistema](#alcance-objetivo)
   - [2.2 Dentro del alcance](#alcance-dentro)
   - [2.3 Fuera del alcance](#alcance-fuera)
   - [2.4 Supuestos y restricciones](#alcance-supuestos)
3. [Dominio del problema](#dominio)
   - [3.1 Descripción del negocio](#dominio-negocio)
   - [3.2 Proceso actual y proceso propuesto](#dominio-procesos)
   - [3.3 Entidades del dominio](#dominio-entidades)
   - [3.4 Estados de las entidades](#dominio-estados)
   - [3.5 Reglas de negocio](#dominio-reglas)
   - [3.6 Glosario](#dominio-glosario)
4. [Actores y permisos](#actores)
5. [Requerimientos funcionales por módulo](#rf)
   - [M01. Autenticación y sesión](#m01)
   - [M02. Usuarios, roles y permisos](#m02)
   - [M03. Instituciones](#m03)
   - [M04. Combustibles y precios](#m04)
   - [M05. Órdenes de compra](#m05)
   - [M06. Lectura de órdenes con OCR](#m06)
   - [M07. Vales de combustible](#m07)
   - [M08. Consumos](#m08)
   - [M09. Despachador de saldo y consumo](#m09)
   - [M10. Reportes, gráficos y exportación](#m10)
   - [M11. Auditoría e integridad de saldos](#m11)
   - [M12. Configuración del sistema](#m12)
6. [Resumen de requerimientos](#resumen)
7. [Trazabilidad con los objetivos del sistema](#trazabilidad)
8. [Decisiones confirmadas y puntos por confirmar](#pendientes)
   - [8.1 Decisiones confirmadas](#decisiones)
   - [8.2 Puntos por confirmar](#puntos)

---

<a id="intro"></a>

## 1. Introducción

<a id="intro-proposito"></a>

### 1.1 Propósito

Este documento define **qué debe hacer** el sistema, sin indicar cómo se construye. Sirve como acuerdo entre quien desarrolla y la estación de servicio San José, y como base para el diseño técnico, las pruebas de aceptación y la planificación del desarrollo.

Los requerimientos no funcionales (rendimiento, seguridad, disponibilidad, respaldo, etc.) y las decisiones de arquitectura se documentan aparte.

<a id="intro-convenciones"></a>

### 1.2 Convenciones del documento

**Identificadores.** Cada requerimiento se identifica como `RF-<MÓDULO>-<NN>`, por ejemplo `RF-VAL-03`. Dentro de cada módulo se escribe solo `<MÓDULO>-<NN>`.

**Estructura de cada requerimiento:**
- **Prioridad, Actor y Objetivo** en una línea.
- **Descripción:** qué debe hacer el sistema.
- **Criterios de aceptación:** condiciones verificables con una prueba. Cuando un requerimiento tiene reglas o validaciones propias, se listan dentro de los criterios.

**Prioridad:**
- **Alta:** imprescindible para operar el sistema.
- **Media:** importante; el sistema funciona sin ella, pero con limitaciones.
- **Baja:** deseable; se implementa si el tiempo lo permite.

**Actores:** Administrador, Oficina, Despachador, Sistema (procesos automáticos) y Servicio OCR. Se describen en la sección 4.

**Objetivo del sistema al que contribuye el requerimiento:**
- **Registro ágil:** registrar órdenes de compra en menos tiempo y con menos errores de digitación.
- **Saldos exactos:** que el saldo de cada vale sea siempre el correcto.
- **Consulta rápida:** consultar saldo y consumo de forma inmediata.
- **Soporte:** requerimiento que hace posible el sistema (acceso, auditoría, configuración, reportes).

**Referencias.** `D-01`, `D-02` remiten a decisiones ya confirmadas; `P-01`, `P-02`, etc. remiten a puntos aún por confirmar. Ambos están en la sección 8. `RN-01`, etc. remiten a las reglas de negocio de la sección 3.5.

[↑ Volver al índice](#indice)

---

<a id="alcance"></a>

## 2. Alcance

<a id="alcance-objetivo"></a>

### 2.1 Objetivo del sistema

Automatizar el registro de órdenes de compra institucionales (con apoyo de OCR), la emisión de vales de combustible, el control exacto de sus saldos y la consulta rápida de saldo y consumo por institución y por periodo, en la estación de servicio San José de Abancay.

<a id="alcance-dentro"></a>

### 2.2 Dentro del alcance

- **Acceso y usuarios:** inicio de sesión, tres roles (Administrador, Oficina y Despachador) y gestión de cuentas.
- **Instituciones:** registro y consulta de las entidades que presentan órdenes de compra, con su modalidad de numeración de vales.
- **Combustibles y precios:** catálogo de combustibles y precio por galón con histórico.
- **Órdenes de compra:** registro manual y con lectura automática (OCR), documento original, estados, cierre y anulación.
- **Lectura con OCR:** extracción de los datos de la orden, revisión junto al documento original y confirmación obligatoria.
- **Vales:** emisión de uno o varios vales por orden con conversión de galones a soles, código único, control contra el presupuesto, vales emitidos por las entidades, estados, anulación, ajuste e impresión.
- **Consumos:** registro de consumos parciales bajo el mismo código de vale, con saldo actualizado al instante y correcciones trazables.
- **Consultas:** saldo y consumo por vale, orden, institución y estación, con actualización inmediata compartida entre estaciones.
- **Reportes:** panel de inicio, gráficos interactivos de consumo (diario, semanal y mensual) y exportación a Excel y PDF para Oficina y Administrador.
- **Control:** auditoría de acciones y verificación automática de la exactitud de los saldos.
- **Configuración:** parámetros del sistema y datos de la estación.

<a id="alcance-fuera"></a>

### 2.3 Fuera del alcance

- Venta de combustible al público general y órdenes de venta: el sistema atiende solo la relación con instituciones mediante órdenes de compra y vales.
- Facturación electrónica y conexión con SUNAT.
- Control de inventario de tanques, surtidores o existencias de combustible: el sistema controla saldos de vales, no existencias físicas.
- Integración con surtidores, puntos de venta u otros sistemas de la estación: el consumo se registra manualmente en el sistema.
- Contabilidad, cobranzas y pagos.
- Aplicación móvil nativa: se usa la aplicación web, adaptada a pantallas pequeñas.
- Portal para que las instituciones consulten su propio saldo: los usuarios son solo el personal de la estación.
- Lectura OCR de vales físicos: el OCR se aplica únicamente a órdenes de compra.
- Instrumentos de la investigación de tesis (encuestas, mediciones de tiempos para el estudio y selección de la muestra): no forman parte del sistema.

<a id="alcance-supuestos"></a>

### 2.4 Supuestos y restricciones

**Supuestos:**
- Los usuarios son aproximadamente 7 personas del personal de la estación.
- El volumen es de entre 25 y 35 órdenes de compra por mes.
- Las órdenes llegan como documento digital (PDF), escaneo o foto, y son legibles.
- Hay conexión a internet estable en el punto de uso.
- La estación cuenta con una cuenta de correo para los mensajes del sistema (ver P-08).
- El presupuesto de las órdenes está en soles y los vales en galones; el precio del combustible varía y se registra en el sistema (D-01).

**Restricciones:**
- **Técnica:** frontend Angular 21.2.0, backend FastAPI y base de datos compartida por las estaciones. El OCR procesa PDF e imágenes con RapidOCR.
- **De proceso:** todo dato leído por OCR requiere revisión y confirmación humana antes de ser definitivo (RN-10).
- **De integridad:** el saldo de un vale nunca se edita directamente; solo cambia mediante movimientos registrados (RN-08).

[↑ Volver al índice](#indice)

---

<a id="dominio"></a>

## 3. Dominio del problema

<a id="dominio-negocio"></a>

### 3.1 Descripción del negocio

La estación de servicio San José, en Abancay, atiende a instituciones (municipalidades, empresas y otras entidades) que le presentan **órdenes de compra**. Cada orden de compra tiene un **presupuesto asignado, en soles**, para el consumo de combustible.

A partir de cada orden se emiten **uno o varios vales de combustible**. Los vales se expresan en **galones**: como el precio del combustible varía, la conversión de soles a galones se hace con el precio vigente del combustible (D-01). Un vale tiene un **código único** y una cantidad inicial (por ejemplo, 100 galones). Se consume de forma **parcial** bajo el mismo código: si se despachan 30 galones, el saldo pasa a 70 y el vale sigue disponible hasta agotarse.

Los vales los emite la estación; además, las entidades generan sus propios vales, que siempre se vinculan a una orden (D-02). Algunas entidades usan una **numeración general** y otras generan una serie de vales **para cada orden**, cuya numeración se agota. Por eso el número de un vale de entidad puede repetirse entre órdenes, y el sistema asigna a cada vale un código interno único.

<a id="dominio-procesos"></a>

### 3.2 Proceso actual y proceso propuesto

**Proceso actual (con Excel):**
1. La institución entrega la orden de compra a la estación.
2. Una persona digita manualmente los datos de la orden en una hoja de Excel.
3. Se emiten los vales y se anotan manualmente.
4. Cada consumo se descuenta a mano en Excel.
5. Para saber el saldo o el consumo de una institución se busca y se calcula en las hojas.
6. Consecuencias: demora en el registro, errores de digitación, saldos desactualizados o inconsistentes y consultas lentas.

**Proceso propuesto (con el sistema):**
1. La institución entrega la orden de compra.
2. Oficina carga el documento de la orden; el sistema lo lee con RapidOCR y propone los datos.
3. Oficina revisa y corrige los datos junto al documento original, y confirma.
4. Oficina emite o registra vales; el sistema genera los códigos y valida contra el presupuesto.
5. Despachador identifica el vale y registra rápidamente el consumo en soles o galones; el saldo se actualiza al instante para todas las estaciones.
6. Oficina y Administrador consultan saldos, consumos, reportes y gráficos.
7. El sistema verifica a diario que los saldos coincidan con la suma de movimientos.

<a id="dominio-entidades"></a>

### 3.3 Entidades del dominio

- **Usuario:** persona de la estación que usa el sistema. Atributos: nombre, correo, rol, estación asignada (cuando corresponda), estado (activo o inactivo), indicador de cambio obligatorio de contraseña.
- **Estación de servicio:** sede donde se emite o consume combustible. Atributos: nombre, dirección, estado. Todas las sedes operan sobre el mismo registro central de órdenes, vales y movimientos.
- **Institución:** entidad que presenta órdenes de compra. Atributos: nombre o razón social, RUC, tipo (municipalidad, empresa u otra), teléfono, correo, dirección, representante, estado, modalidad de numeración de sus vales (general, por orden o no aplica). Tiene muchas órdenes.
- **Tipo de combustible:** catálogo de combustibles. Atributos: nombre, estado. Tiene un historial de precios.
- **Precio de combustible:** precio por galón desde una fecha. Atributos: combustible, precio por galón, fecha de vigencia, usuario que lo registró.
- **Orden de compra:** documento con presupuesto asignado. Atributos: número, institución, fecha de emisión, presupuesto en soles, combustible (opcional), estado, archivo original, indicador de registro con OCR, serie de numeración autorizada (si aplica), observaciones. Pertenece a una institución y tiene uno o varios vales.
- **Vale:** autorización de consumo de una cantidad de combustible. Atributos: código interno único, número de la entidad (si aplica), orden, emisor (estación o entidad), combustible, cantidad inicial en galones, precio por galón aplicado, valor en soles, saldo en galones, fecha de emisión, fecha de vencimiento, estado. Pertenece a una orden y tiene muchos movimientos.
- **Movimiento de vale:** cada cambio de saldo de un vale. Atributos: tipo (emisión, consumo, anulación, ajuste, reversión), variación de galones (con signo), saldo posterior, fecha y hora, usuario, estación de servicio, motivo u observación, placa y conductor (opcionales); cantidad en galones, precio aplicado e importe en soles cuando corresponda.
- **Extracción OCR:** resultado de la lectura automática de un documento. Atributos: archivo, estado, método (texto digital u OCR), valores extraídos con su confianza, valores finales confirmados, campos corregidos, tiempo de proceso, versión del procesamiento. Origina una orden al confirmarse.
- **Parámetro del sistema:** valor configurable que ajusta el funcionamiento (umbrales, límites, formatos).
- **Registro de auditoría:** huella de una acción sensible. Atributos: usuario, acción, entidad afectada, valores anteriores y nuevos, fecha y hora.
- **Verificación de integridad:** resultado de comparar cada saldo con la suma de sus movimientos. Atributos: fecha, vales revisados, diferencias encontradas (vale, saldo almacenado, saldo recalculado, revisada, comentario).

<a id="dominio-estados"></a>

### 3.4 Estados de las entidades

**Orden de compra:**
- **Borrador:** registrada con datos incompletos; aún no emite vales. Pasa a vigente o a anulada.
- **Vigente:** registrada y completa; puede emitir vales. Pasa a cerrada, o a anulada (solo si no tiene consumos).
- **Cerrada:** finalizada; no admite nuevos vales. No cambia de estado.
- **Anulada:** invalidada con motivo; no admite vales ni consumos. No cambia de estado.

**Vale:**
- **Activo:** tiene saldo y puede consumirse. Pasa a agotado, vencido o anulado.
- **Agotado:** saldo igual a cero. Solo un ajuste autorizado del administrador puede reactivarlo.
- **Vencido:** superó su fecha de vencimiento. Solo un ajuste autorizado del administrador puede reactivarlo.
- **Anulado:** invalidado con motivo; saldo en cero. No cambia de estado.

**Extracción OCR:**
- **Pendiente:** archivo recibido. Pasa a procesando.
- **Procesando:** el documento se está leyendo. Pasa a lista o a fallida.
- **Lista:** datos extraídos, esperando revisión. Pasa a confirmada o a descartada.
- **Fallida:** no se pudo leer el documento. Pasa a pendiente (reintento) o a descartada.
- **Confirmada:** el usuario revisó y creó la orden. No cambia de estado.
- **Descartada:** cancelada por el usuario. No cambia de estado.

<a id="dominio-reglas"></a>

### 3.5 Reglas de negocio

- **RN-01.** Toda orden de compra pertenece a una sola institución y tiene un presupuesto asignado, en soles, mayor que cero. *Requerimientos:* ORD-01.
- **RN-02.** Una orden puede tener uno o varios vales. *Requerimientos:* VAL-01, VAL-04, VAL-05.
- **RN-03.** El valor en soles de los vales de una orden (galones por precio por galón aplicado al emitir) no puede exceder su presupuesto (D-01). *Requerimientos:* VAL-03, CMB-04.
- **RN-04.** Cada vale tiene un código interno único e inmutable, y todos sus consumos se registran bajo ese mismo vale. *Requerimientos:* VAL-02, CON-01.
- **RN-05.** El consumo puede ser parcial. El saldo es la cantidad inicial más las variaciones de todos sus movimientos (consumos, anulaciones, reversiones y ajustes). *Requerimientos:* CON-02.
- **RN-06.** Un consumo no puede exceder el saldo disponible; el saldo nunca es negativo. *Requerimientos:* CON-03, CON-08.
- **RN-07.** Un vale agotado, anulado o vencido no admite consumos. *Requerimientos:* CON-04, VAL-08.
- **RN-08.** El saldo no se edita directamente; solo cambia mediante movimientos registrados. *Requerimientos:* VAL-11, VAL-14, AUD-05.
- **RN-09.** Las anulaciones, reversiones y ajustes solo las realiza el Administrador, con motivo obligatorio, y quedan auditadas. *Requerimientos:* ORD-09, VAL-10, VAL-11, CON-11.
- **RN-10.** Ningún dato leído por OCR se vuelve definitivo sin la confirmación del usuario. *Requerimientos:* OCR-07.
- **RN-11.** No se eliminan físicamente órdenes, vales, movimientos ni registros de auditoría. *Requerimientos:* VAL-14, AUD-02.
- **RN-12.** El número de orden es único por institución y año. *Requerimientos:* ORD-02.
- **RN-13.** Una orden anulada no admite nuevos vales ni consumos; una orden cerrada no admite nuevos vales. *Requerimientos:* ORD-09, ORD-10.
- **RN-14.** Los vales emitidos por la entidad siempre se vinculan a una orden y siguen las mismas reglas de saldo y consumo que los de la estación (D-02). *Requerimientos:* VAL-05.
- **RN-15.** El número de un vale de entidad es único según la modalidad de la institución: dentro de la institución si usa numeración general, y dentro de la orden si usa numeración por orden (D-02). *Requerimientos:* VAL-05, VAL-15.
- **RN-16.** El precio por galón aplicado a un vale es el vigente del combustible al emitirlo y queda registrado con el vale (por confirmar, P-10). *Requerimientos:* VAL-01, CMB-02.
- **RN-17.** Una orden con consumos registrados no puede anularse; solo puede cerrarse (por confirmar, P-04). *Requerimientos:* ORD-09.
- **RN-18.** Al anular un vale, se libera del presupuesto de la orden solo la parte no consumida (por confirmar, P-13). *Requerimientos:* VAL-10, VAL-03.

<a id="dominio-glosario"></a>

### 3.6 Glosario

- **Orden de compra:** documento que una institución entrega a la estación con un presupuesto asignado para consumir combustible.
- **Presupuesto:** monto en soles asignado en la orden de compra, que limita el valor de los vales que se pueden emitir.
- **Vale:** comprobante emitido a partir de una orden que autoriza el consumo de una cantidad de combustible, expresada en galones.
- **Código interno:** identificador único que el sistema asigna a cada vale; con él se consume el vale las veces que haga falta hasta agotar su saldo.
- **Número de la entidad:** numeración propia que una entidad asigna a sus vales; puede repetirse entre órdenes si la entidad usa numeración por orden.
- **Numeración general:** modalidad en que la entidad numera sus vales de forma continua para todas sus órdenes.
- **Numeración por orden:** modalidad en que la entidad genera una serie de vales para cada orden, y esa serie se agota.
- **Saldo:** cantidad de galones que aún puede consumirse con un vale.
- **Consumo parcial:** despacho de una cantidad menor al saldo del vale, que deja el resto disponible bajo el mismo código.
- **Movimiento:** registro de cada cambio en el saldo de un vale (emisión, consumo, anulación, ajuste o reversión).
- **Emisor:** quien genera el vale: la estación de servicio o la entidad.
- **Precio por galón vigente:** precio del combustible registrado en el sistema para una fecha; se usa para convertir galones a soles.
- **Valor del vale:** cantidad de galones por el precio por galón aplicado al emitirlo.
- **Institución o entidad:** organización cliente que presenta órdenes de compra (municipalidad, empresa, etc.).
- **OCR:** reconocimiento óptico de caracteres; tecnología que lee el texto de un documento escaneado o fotografiado.
- **Confianza:** nivel de seguridad (entre 0 y 1) con que el OCR da por correcto un campo leído.
- **Revisión:** paso en que el usuario compara el documento original con los datos extraídos y los corrige antes de confirmar.

[↑ Volver al índice](#indice)

---

<a id="actores"></a>

## 4. Actores y permisos

### 4.1 Actores

- **Administrador:** responsable del sistema. Accede a todos los módulos y gestiona usuarios, precios, anulaciones, ajustes, auditoría y configuración.
- **Oficina:** gestiona instituciones, órdenes, OCR, vales, precios, consultas y reportes.
- **Despachador:** personal de despacho con acceso limitado al registro de consumos de vales.
- **Sistema:** procesos automáticos (vencimiento de vales, verificación de saldos, procesamiento de OCR).
- **Servicio OCR:** capacidad interna que lee documentos y devuelve los campos extraídos. No interactúa con personas.

### 4.2 Permisos por rol

**Administrador** tiene acceso a todos los módulos, incluidos los de Oficina y Despachador, y además:
- Gestionar usuarios y roles.
- Desactivar y reactivar instituciones.
- Administrar el catálogo de combustibles y registrar precios.
- Anular órdenes.
- Anular vales, revertir consumos y ajustar saldos.
- Ver la bitácora de auditoría y la verificación de integridad.
- Ver el historial de extracciones OCR.
- Administrar parámetros y datos de la estación.

**Oficina** puede:
- Registrar instituciones y órdenes, cargar PDF o imágenes, revisar y confirmar la extracción OCR.
- Crear y administrar vales; consultar órdenes, saldos y movimientos.
- Consultar reportes interactivos y exportar resultados.
- Gestionar la operación diaria, sin acceso a gestión de usuarios ni auditoría administrativa.

**Despachador** puede:
- Buscar un vale vigente y consultar los datos mínimos para atenderlo.
- Registrar consumos parciales indicando cantidad y tipo de combustible. El importe se calcula con el precio aplicado al vale.
- Ver la confirmación y el saldo actualizado.
- No puede acceder a OCR, órdenes, administración de vales, instituciones, precios, reportes, usuarios, configuración ni auditoría. El backend aplica las mismas restricciones que la interfaz.

[↑ Volver al índice](#indice)

---

<a id="rf"></a>

## 5. Requerimientos funcionales por módulo

<a id="m01"></a>

### M01. Autenticación y sesión

Controla quién entra al sistema y qué puede hacer.

#### RF-AUT-01. Inicio de sesión
**Prioridad:** Alta · **Actor:** Todos · **Objetivo:** Soporte
**Descripción:** El usuario accede con correo y contraseña y verificación reCAPTCHA v3. El backend valida token, acción, hostname y score mínimo. La API emite un JWT de acceso de vida corta y un refresh token rotatorio.
**Criterios de aceptación:**
- Con credenciales válidas ingresa al panel de inicio.
- Con credenciales inválidas se muestra un mensaje genérico que no revela cuál dato falló.
- Un usuario inactivo no puede iniciar sesión, aunque sus credenciales sean correctas.
- Cada inicio de sesión y cada intento fallido queda registrado (AUD-01).
- La contraseña nunca se almacena en texto plano; se conserva mediante hash adaptativo con sal. La transmisión ocurre por HTTPS y las llaves secretas se mantienen solo en configuración protegida del servidor.
- Un score inferior al umbral configurable rechaza el acceso sin revelar detalles sensibles.
- Los refresh tokens se almacenan protegidos, rotan en cada uso y pueden revocarse; los secretos y tokens no aparecen en logs.

#### RF-AUT-02. Cierre de sesión
**Prioridad:** Alta · **Actor:** Todos · **Objetivo:** Soporte
**Descripción:** El usuario cierra su sesión desde cualquier pantalla.
**Criterios de aceptación:**
- La sesión queda invalidada.
- Al volver atrás en el navegador no se muestran datos protegidos.

#### RF-AUT-03. Cuentas sin autorregistro
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** Solo el administrador crea cuentas de usuario.
**Criterios de aceptación:**
- No existe ninguna ruta ni formulario de registro público.
- Una cuenta nueva solo existe si un administrador la creó (USR-01).

#### RF-AUT-04. Bloqueo por intentos fallidos
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema limita los intentos consecutivos de inicio de sesión.
**Criterios de aceptación:**
- Tras 5 intentos fallidos consecutivos (valor configurable en CFG-01) se bloquea temporalmente el acceso.
- El mensaje informa el tiempo de espera restante.
- Pasado el tiempo de bloqueo, el usuario puede intentar de nuevo.

#### RF-AUT-05. Recuperación de contraseña
**Prioridad:** Media · **Actor:** Todos · **Objetivo:** Soporte
**Descripción:** El usuario solicita restablecer su contraseña mediante un enlace enviado a su correo (ver P-08).
**Criterios de aceptación:**
- El enlace es de un solo uso y vence en un tiempo definido.
- El mensaje de la solicitud no revela si el correo existe en el sistema.
- Al usar el enlace se exige una contraseña nueva válida (RF-AUT-06).

#### RF-AUT-06. Cambio de contraseña
**Prioridad:** Media · **Actor:** Todos · **Objetivo:** Soporte
**Descripción:** El usuario autenticado cambia su propia contraseña.
**Criterios de aceptación:**
- Se solicita la contraseña actual.
- La nueva contraseña tiene al menos 8 caracteres y es distinta de la actual.
- El cambio queda registrado en la auditoría.

#### RF-AUT-07. Cambio obligatorio de contraseña
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** Un usuario con contraseña temporal debe cambiarla antes de usar el sistema.
**Criterios de aceptación:**
- Tras el primer inicio de sesión, o tras un restablecimiento por el administrador, solo se puede acceder a la pantalla de cambio de contraseña.
- Hasta cambiarla, cualquier otra ruta redirige a esa pantalla.
- Al cambiarla, se retira la condición y se accede al panel.

#### RF-AUT-08. Expiración por inactividad
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** La sesión se cierra tras un periodo sin actividad.
**Criterios de aceptación:**
- Pasado el tiempo configurado (CFG-01), se pide iniciar sesión de nuevo.
- Al volver a ingresar, se retorna a la pantalla en la que estaba el usuario.
- Un formulario a medias no deja el sistema en un estado inconsistente.

#### RF-AUT-09. Control de acceso por rol
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** Cada pantalla y acción se habilita según el rol del usuario (sección 4.2).
**Criterios de aceptación:**
- Una acción no permitida se rechaza en el servidor con una pantalla de acceso denegado, incluso si se accede por dirección directa.
- El menú muestra solo lo permitido al rol.
- Cada acción sensible se autoriza de nuevo al ejecutarse, no solo al abrir la pantalla.

[↑ Volver al índice](#indice)

---

<a id="m02"></a>

### M02. Usuarios, roles y permisos

Administración de las cuentas del personal que usa el sistema.

#### RF-USR-01. Crear usuario
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador registra un usuario con nombre, correo, rol y contraseña temporal.
**Criterios de aceptación:**
- El correo es obligatorio, tiene formato válido y no puede repetirse.
- La contraseña temporal se muestra una sola vez al crear.
- El usuario queda marcado para cambiar la contraseña en su primer inicio (RF-AUT-07).
- La creación queda auditada.

#### RF-USR-02. Listar y buscar usuarios
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador consulta los usuarios existentes.
**Criterios de aceptación:**
- Búsqueda por nombre o correo.
- Filtros por rol y por estado (activo o inactivo).
- Listado paginado.

#### RF-USR-03. Editar usuario
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador modifica nombre, correo o rol de un usuario.
**Criterios de aceptación:**
- Los cambios se guardan y quedan auditados con valores anteriores y nuevos.
- No se admiten correos duplicados.

#### RF-USR-04. Asignar rol
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador asigna a cada usuario uno de los tres roles: Administrador, Oficina o Despachador.
**Criterios de aceptación:**
- Cada usuario tiene exactamente un rol.
- El cambio rige desde la siguiente acción del usuario.

#### RF-USR-05. Activar y desactivar usuario
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador habilita o bloquea el acceso de un usuario sin borrarlo.
**Criterios de aceptación:**
- Un usuario desactivado no puede iniciar sesión y sus sesiones abiertas se cierran.
- Su historial (órdenes, consumos, auditoría) se conserva.
- No se elimina físicamente (RN-11).

#### RF-USR-06. Restablecer contraseña de un usuario
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador genera una contraseña temporal para otro usuario.
**Criterios de aceptación:**
- La contraseña temporal se muestra una sola vez.
- El usuario debe cambiarla en su siguiente inicio de sesión (RF-AUT-07).
- La acción queda auditada.

#### RF-USR-07. Protección del último administrador
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema impide quedarse sin administradores activos.
**Criterios de aceptación:**
- No se permite desactivar ni cambiar de rol al único administrador activo.
- Se muestra un mensaje que explica el motivo.

[↑ Volver al índice](#indice)

---

<a id="m03"></a>

### M03. Instituciones

Registro de las entidades que presentan órdenes de compra.

#### RF-INS-01. Registrar institución
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** Se registra una institución con nombre o razón social, RUC, tipo (municipalidad, empresa u otra), teléfono, correo, dirección y representante. Si la institución genera vales propios, se indica su modalidad de numeración: general o por orden (D-02).
**Criterios de aceptación:**
- Nombre, RUC y tipo son obligatorios.
- El RUC tiene 11 dígitos, un dígito verificador válido y es único; si ya existe, se informa y se enlaza a la institución existente.
- La modalidad de numeración es obligatoria cuando la institución genera vales propios.
- El alta queda auditada.

#### RF-INS-02. Editar institución
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se modifican los datos de una institución.
**Criterios de aceptación:**
- Los cambios quedan auditados con valores anteriores y nuevos.
- El RUC solo puede modificarse si la institución no tiene órdenes registradas, o por el administrador.
- Cambiar la modalidad de numeración no altera los vales ya registrados.

#### RF-INS-03. Listar y buscar instituciones
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consulta el listado de instituciones.
**Criterios de aceptación:**
- Búsqueda por nombre o RUC.
- Filtro por estado (activa o inactiva).
- Listado paginado.

#### RF-INS-04. Ficha de la institución
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se muestra un resumen de la institución.
**Criterios de aceptación:**
- Muestra sus datos, sus órdenes, el saldo total vigente y el consumo del mes.
- Ofrece accesos directos a sus órdenes, vales y estado de cuenta.

#### RF-INS-05. Desactivar y reactivar institución
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador inhabilita una institución sin borrarla.
**Criterios de aceptación:**
- Una institución inactiva no admite nuevas órdenes.
- Su historial (órdenes, vales y consumos) se conserva y sigue consultable.
- No se elimina físicamente (RN-11).

[↑ Volver al índice](#indice)

---

<a id="m04"></a>

### M04. Combustibles y precios

Catálogo de combustibles y precio por galón, base de la conversión de soles a galones (D-01).

#### RF-CMB-01. Catálogo de combustibles
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador gestiona los tipos de combustible (por ejemplo Diésel B5, Gasohol 90, Gasohol 95 y GLP).
**Criterios de aceptación:**
- Permite crear, editar y activar o desactivar tipos.
- Un tipo en uso no se elimina.
- Un tipo inactivo no se puede elegir en nuevas órdenes ni vales.

#### RF-CMB-02. Registrar precio por galón
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador registra el precio por galón de un combustible con su fecha de vigencia, porque el precio varía.
**Criterios de aceptación:**
- El precio es mayor que cero y tiene hasta 2 decimales.
- La fecha de vigencia no puede ser anterior a la del último precio registrado para ese combustible.
- Los precios registrados no se editan ni se eliminan; un cambio se registra como un precio nuevo.
- Un nuevo precio no modifica los vales ya emitidos (RN-16, ver P-10).
- Cada registro queda auditado.

#### RF-CMB-03. Consultar precio vigente e histórico
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se consulta el precio vigente de un combustible a una fecha y su histórico.
**Criterios de aceptación:**
- El precio vigente a una fecha es el último registrado con vigencia menor o igual a esa fecha.
- El histórico muestra cada precio, su fecha de vigencia y quién lo registró, del más reciente al más antiguo.
- Si no hay precio vigente a la fecha consultada, se informa claramente.

#### RF-CMB-04. Cálculo del valor en soles
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema convierte galones a soles con el precio vigente del combustible.
**Criterios de aceptación:**
- Valor en soles = cantidad en galones × precio por galón vigente, redondeado a 2 decimales (mitad hacia arriba).
- Sin precio vigente para el combustible no se permite emitir vales; se muestra un mensaje que lo explica.
- La conversión se usa en la emisión de vales (VAL-01), en el control contra el presupuesto (VAL-03) y en las consultas.

[↑ Volver al índice](#indice)

---

<a id="m05"></a>

### M05. Órdenes de compra

Registro, seguimiento y cierre de las órdenes con presupuesto asignado en soles.

#### RF-ORD-01. Registro manual de orden
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** Se registra una orden indicando institución, número, fecha de emisión, presupuesto en soles, tipo de combustible (opcional) y observaciones. Si la institución usa numeración por orden, también se registra la serie autorizada (VAL-15). El registro manual sirve además como respaldo cuando el OCR no está disponible.
**Criterios de aceptación:**
- Institución, número, fecha y presupuesto son obligatorios.
- El presupuesto está en soles y es mayor que cero.
- La fecha de emisión no es futura.
- Una institución inactiva no puede elegirse.
- Se puede guardar como borrador o como vigente.
- El registro queda auditado.

#### RF-ORD-02. Número de orden único
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema evita órdenes repetidas.
**Criterios de aceptación:**
- No se admiten dos órdenes con el mismo número en la misma institución y año (RN-12).
- El mensaje de rechazo enlaza a la orden existente.

#### RF-ORD-03. Adjuntar documento original
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** Se adjunta el archivo de la orden (PDF, JPG o PNG).
**Criterios de aceptación:**
- El tipo se valida por el contenido real del archivo, no solo por su extensión.
- El tamaño máximo es configurable (por defecto 10 MB; CFG-01).
- Los archivos no permitidos se rechazan con un mensaje claro.
- El archivo no es accesible por una dirección pública; solo usuarios autorizados lo ven.

#### RF-ORD-04. Visualizar documento original
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se abre el archivo adjunto desde el detalle de la orden.
**Criterios de aceptación:**
- Los PDF se muestran en un visor integrado; las imágenes, con zoom.
- Solo lo ven usuarios autorizados.

#### RF-ORD-05. Listado y filtros de órdenes
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consultan las órdenes registradas.
**Criterios de aceptación:**
- Filtros por institución, estado, rango de fechas y número.
- Orden por fecha descendente.
- Listado paginado.
- Los filtros se conservan en la dirección de la página para poder recargarla o compartirla.

#### RF-ORD-06. Detalle de la orden
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se muestra toda la información de una orden.
**Criterios de aceptación:**
- Presenta presupuesto en soles, total emitido en soles y en galones, presupuesto restante por emitir en soles y consumo acumulado en galones.
- Lista los vales asociados con su estado y saldo.
- Muestra estado, usuario que la registró, fecha e historial de cambios (AUD-04).

#### RF-ORD-07. Edición controlada
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Saldos exactos
**Descripción:** Se limita qué se puede editar según el avance de la orden.
**Criterios de aceptación:**
- Sin vales emitidos se pueden editar todos los campos.
- Con vales emitidos solo se pueden editar observaciones y adjuntos.
- Una orden cerrada o anulada no se edita.
- Toda edición queda auditada.

#### RF-ORD-08. Estados de la orden
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** La orden transita por estados definidos.
**Criterios de aceptación:**
- Los estados son borrador, vigente, cerrada y anulada.
- Solo se permiten las transiciones de la sección 3.4; cualquier otra se rechaza con mensaje.

#### RF-ORD-09. Anulación de orden
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador invalida una orden.
**Criterios de aceptación:**
- Exige un motivo.
- No se puede anular una orden con consumos registrados: solo se cierra (RN-17, ver P-04).
- Al anularse, sus vales sin consumo se anulan y no se admiten nuevos vales ni consumos (RN-13).
- La anulación queda auditada (RN-09).

#### RF-ORD-10. Cierre de orden
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se finaliza una orden.
**Criterios de aceptación:**
- Requiere confirmación.
- El sistema sugiere el cierre cuando todos sus vales están agotados, anulados o vencidos.
- Una orden cerrada no admite nuevos vales; los vales con saldo siguen disponibles hasta agotarse o vencer.

#### RF-ORD-11. Alerta de posible duplicado
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema advierte sobre órdenes que podrían estar repetidas.
**Criterios de aceptación:**
- Al guardar, si existe otra orden de la misma institución con igual presupuesto y fecha, se muestra una advertencia con enlace a esa orden.
- El usuario decide continuar o cancelar.

[↑ Volver al índice](#indice)

---

<a id="m06"></a>

### M06. Lectura de órdenes con OCR

Extracción automática de los datos de la orden de compra, con revisión humana obligatoria.

#### RF-OCR-01. Carga de documento
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** El usuario sube la orden de compra para su lectura automática.
**Criterios de aceptación:**
- Acepta PDF, JPG y PNG hasta el tamaño máximo configurado.
- Rechaza otros tipos y tamaños con un mensaje claro.
- En celular permite capturar la foto con la cámara; en escritorio, arrastrar y soltar.
- Muestra una vista previa del archivo antes de procesarlo.

#### RF-OCR-02. Procesamiento con estado visible
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Registro ágil
**Descripción:** El documento se procesa mostrando su avance al usuario.
**Criterios de aceptación:**
- Se muestran los estados pendiente, procesando, lista o fallida.
- Mientras se procesa, el usuario ve que el sistema está trabajando y cuánto lleva esperando.
- Si la espera se prolonga, se ofrece continuar con el registro manual sin perder el archivo subido.

#### RF-OCR-03. Extracción de campos
**Prioridad:** Alta · **Actor:** Servicio OCR · **Objetivo:** Registro ágil
**Descripción:** El servicio OCR extrae los datos de la orden.
**Criterios de aceptación:**
- Extrae número de orden, nombre de la entidad, RUC, fecha, presupuesto, tipo de combustible, precio por galón y cantidad/galones cuando existan en el documento (campos exactos según P-05).
- Un campo no encontrado queda vacío; nunca se inventa un valor.
- Para PDF con texto digital usa ese texto; para escaneos y fotos aplica reconocimiento óptico.
- Se guarda cómo se leyó el documento (texto digital u OCR) y la versión del procesamiento.

#### RF-OCR-04. Confianza por campo
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Cada campo extraído muestra qué tan seguro es.
**Criterios de aceptación:**
- Cada campo tiene un nivel de confianza.
- Los campos con confianza menor al umbral configurado (CFG-01) se resaltan con color y con texto, no solo con color.
- El texto indica el motivo cuando es un formato inválido.

#### RF-OCR-05. Pantalla de revisión
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** El usuario compara el documento con los datos extraídos.
**Criterios de aceptación:**
- Muestra el documento original, con zoom, junto al formulario con los valores extraídos.
- Todos los campos son editables.
- El usuario puede avanzar entre campos con el teclado y confirmar sin usar el ratón.

#### RF-OCR-06. Validación de formato
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema valida los campos antes de confirmar.
**Criterios de aceptación:**
- RUC de 11 dígitos con dígito verificador válido.
- Fecha válida y no futura.
- Presupuesto numérico mayor que cero.
- Los errores se señalan junto al campo, con el mismo criterio del registro manual.

#### RF-OCR-07. Confirmación obligatoria
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Saldos exactos
**Descripción:** La orden solo se crea cuando el usuario confirma lo revisado (RN-10).
**Criterios de aceptación:**
- El botón de confirmar se habilita con los campos obligatorios completos y la marca "datos revisados".
- Sin confirmación no se crea ninguna orden definitiva.
- Al confirmar, la orden se crea con las mismas reglas del registro manual (RF-ORD-01 y RF-ORD-02).
- La orden creada queda marcada como registrada con OCR.

#### RF-OCR-08. Vinculación de institución por RUC
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Registro ágil
**Descripción:** El sistema asocia la institución usando el RUC extraído.
**Criterios de aceptación:**
- Si el RUC existe, preselecciona la institución.
- Si no existe, ofrece registrarla sin perder lo ya capturado.

#### RF-OCR-09. Contingencia ante fallas
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Registro ágil
**Descripción:** El usuario puede continuar su trabajo si el OCR falla.
**Criterios de aceptación:**
- Si el servicio no responde, falla o no reconoce el documento, se informa el motivo con un mensaje claro.
- Se ofrece continuar con el registro manual conservando el archivo ya subido.
- Una falla del OCR nunca bloquea el registro de órdenes.

#### RF-OCR-10. Reintento de procesamiento
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se vuelve a procesar una extracción fallida.
**Criterios de aceptación:**
- El reintento no exige subir el archivo de nuevo.
- Se conserva el registro del intento anterior.

#### RF-OCR-11. Registro de correcciones
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema guarda qué corrigió el usuario respecto de lo extraído.
**Criterios de aceptación:**
- Por cada campo se guarda el valor extraído, el valor final y si fue corregido.
- Los datos permiten calcular la precisión del OCR en uso real.

#### RF-OCR-12. Descartar extracción
**Prioridad:** Baja · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** El usuario cancela una extracción sin crear orden.
**Criterios de aceptación:**
- La extracción queda en estado descartada y no genera ninguna orden.

#### RF-OCR-13. Historial de extracciones
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador revisa las extracciones realizadas.
**Criterios de aceptación:**
- Lista fecha, usuario, estado, método de lectura, tiempo de proceso y confianza promedio.
- Filtros por estado y fecha.
- Desde cada fila se accede al documento y al resultado.

[↑ Volver al índice](#indice)

---

<a id="m07"></a>

### M07. Vales de combustible

Emisión y gestión de los vales asociados a cada orden de compra.

#### RF-VAL-01. Emitir vales desde una orden
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** Desde una orden vigente se emiten uno o varios vales indicando tipo de combustible, cantidad en galones y fecha de vencimiento (opcional). El sistema convierte los galones a soles con el precio vigente del combustible (D-01, CMB-04).
**Criterios de aceptación:**
- No se emiten vales sobre órdenes cerradas, anuladas o en borrador.
- Se exige un precio vigente para el combustible.
- Con cada vale se guardan el precio por galón aplicado y su valor en soles (RN-16).
- Cada vale genera su movimiento de emisión.
- La cantidad es mayor que cero y tiene hasta 2 decimales.
- Antes de confirmar se muestra una vista previa con el precio vigente, el valor en soles, el presupuesto restante y el máximo de galones que se podrían emitir.

#### RF-VAL-02. Código interno único de vale
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema genera un código interno para cada vale, sea de la estación o de una entidad.
**Criterios de aceptación:**
- El código es único, tiene formato configurable (por ejemplo VAL-AAAA-NNNNNN; CFG-01) y no puede repetirse ni modificarse (RN-04).
- El código no reemplaza al número de la entidad: ambos se conservan.
- Dos emisiones simultáneas nunca generan el mismo código.

#### RF-VAL-03. Control contra el presupuesto
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema impide emitir más de lo que permite la orden, comparando valores en soles (RN-03).
**Criterios de aceptación:**
- El valor en soles de todos los vales de la orden (galones por precio aplicado al emitir) no puede exceder el presupuesto.
- Si lo excede, se rechaza la emisión y se muestran el presupuesto restante y el máximo de galones que se podrían emitir al precio vigente.
- Un vale anulado libera solo la parte no consumida (RN-18, ver P-13).
- La verificación es exacta aunque dos usuarios emitan al mismo tiempo sobre la misma orden.

#### RF-VAL-04. Emisión múltiple en una operación
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Registro ágil
**Descripción:** Se emiten varios vales de una orden en un solo paso.
**Criterios de aceptación:**
- Se muestra un resumen antes de confirmar (por ejemplo, 3 vales de 100 galones).
- La operación es atómica: se emiten todos o ninguno.
- El control contra el presupuesto considera el total de la operación.

#### RF-VAL-05. Registrar vales emitidos por la entidad
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Saldos exactos
**Descripción:** Se registran los vales que genera la propia entidad. Siempre se vinculan a una orden de compra (D-02, RN-14).
**Criterios de aceptación:**
- Se indican orden, número del vale de la entidad, combustible y cantidad en galones.
- El número es único según la modalidad de la institución: con numeración general no se repite dentro de la institución; con numeración por orden no se repite dentro de la orden (RN-15).
- Un mismo número puede existir en otra orden cuando la institución usa numeración por orden.
- Siguen las mismas reglas de saldo, consumo, estado y presupuesto que los vales de la estación (ver P-11).
- Cada vale recibe su código interno (RF-VAL-02).

#### RF-VAL-06. Listado y búsqueda de vales
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consultan los vales registrados.
**Criterios de aceptación:**
- Búsqueda por código interno o por número de la entidad.
- Filtros por institución, orden, estado, combustible y emisor.
- Cuando un número de entidad coincide con varios vales, se muestran todos con institución, orden y combustible.
- Listado paginado.

#### RF-VAL-07. Detalle del vale
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se muestra toda la información de un vale.
**Criterios de aceptación:**
- Presenta código interno, número de la entidad, orden, cantidad inicial, consumido, saldo actual, precio aplicado, valor en soles y estado.
- Muestra el historial de movimientos (RF-CON-12).

#### RF-VAL-08. Estados del vale
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El vale cambia de estado según su uso.
**Criterios de aceptación:**
- Pasa a agotado cuando el saldo llega a cero, a vencido al superar su fecha de vencimiento y a anulado por acción del administrador.
- Un vale agotado, vencido o anulado no admite consumos (RN-07).
- Un vale vencido se reconoce como tal al consultarlo o consumirlo, aunque el proceso diario aún no lo haya marcado.

#### RF-VAL-09. Vencimiento automático
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema marca los vales vencidos (vigencia según P-02).
**Criterios de aceptación:**
- Un proceso diario cambia a vencido los vales activos cuya fecha de vencimiento ya pasó.
- Los vales sin fecha de vencimiento no vencen.
- El proceso puede ejecutarse también a demanda.

#### RF-VAL-10. Anulación de vale
**Prioridad:** Alta · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador invalida un vale.
**Criterios de aceptación:**
- Exige un motivo (RN-09).
- Se registra un movimiento de anulación por el saldo restante y el saldo queda en cero.
- Libera del presupuesto la parte no consumida (RN-18).
- La anulación queda auditada.

#### RF-VAL-11. Ajuste excepcional de saldo
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador corrige un saldo en casos justificados.
**Criterios de aceptación:**
- Exige un motivo.
- Se registra un movimiento de ajuste con cantidad con signo, saldo previo y saldo posterior (RN-08).
- No puede dejar el saldo negativo.
- El ajuste queda auditado.

#### RF-VAL-12. Impresión del vale
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se genera el vale de la estación en formato imprimible (ver P-01).
**Criterios de aceptación:**
- El PDF incluye código, institución, combustible, cantidad, fecha y un código QR o de barras con el código del vale.
- Reimprimir un vale lo marca como duplicado.

#### RF-VAL-13. Alertas de vales
**Prioridad:** Baja · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema señala vales que requieren atención.
**Criterios de aceptación:**
- Se destacan los vales con saldo bajo (umbral configurable, CFG-01) y los próximos a vencer (días configurables).
- Las alertas aparecen en el panel de inicio y enlazan al listado filtrado.

#### RF-VAL-14. Sin eliminación de vales
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Los vales y sus movimientos no se borran (RN-11).
**Criterios de aceptación:**
- Ningún vale ni movimiento se elimina físicamente, ni siquiera por el administrador.
- Toda corrección se hace mediante un movimiento nuevo.
- Los movimientos registrados no se pueden modificar.

#### RF-VAL-15. Serie de numeración por orden
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Saldos exactos
**Descripción:** Para instituciones con numeración por orden, la orden registra el rango de números autorizado y el sistema controla cuántos quedan (ver P-12).
**Criterios de aceptación:**
- La serie se registra con número inicial y final, y el inicial no supera al final.
- Los números de vales de la entidad deben estar dentro del rango.
- Se muestran los números usados y los disponibles.
- Al agotarse el rango no se registran más vales de esa orden.

[↑ Volver al índice](#indice)

---

<a id="m08"></a>

### M08. Consumos

Registro de cada despacho de combustible contra un vale. Es el módulo que determina la exactitud de los saldos.

#### RF-CON-01. Registro de consumo por código
**Prioridad:** Alta · **Actor:** Despachador, Oficina, Administrador · **Objetivo:** Saldos exactos
**Descripción:** El usuario busca el vale por su código interno o número de entidad y registra los galones despachados o el importe en soles. Si ingresa soles, el sistema convierte el monto a galones usando el precio por galón fijado al vale.
**Criterios de aceptación:**
- Al ingresar el código se muestran institución, orden, combustible y saldo.
- Si el número coincide con varios vales, se elige entre los candidatos antes de continuar.
- Al confirmar se registra el movimiento con usuario, estación, fecha y hora, precio aplicado, importe en soles y galones equivalentes.
- Después de registrar, se muestran el nuevo saldo en galones y el importe registrado, y el formulario queda listo para el siguiente despacho.

#### RF-CON-02. Consumo parcial
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Un vale puede consumirse en varias veces bajo el mismo código (RN-05). Si el despacho se ingresa en soles, el monto se convierte con el precio por galón inmutable del vale.
**Criterios de aceptación:**
- El nuevo saldo es el saldo anterior menos la cantidad consumida (por ejemplo, 100 menos 30 es 70).
- El vale sigue activo mientras tenga saldo.
- El movimiento guarda el saldo posterior.

#### RF-CON-03. Rechazo por saldo insuficiente
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** No se permite consumir más que el saldo (RN-06).
**Criterios de aceptación:**
- Una cantidad mayor al saldo se rechaza con un mensaje que indica el saldo disponible.
- No se registra ningún movimiento ni se modifica el saldo.

#### RF-CON-04. Rechazo por estado del vale
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** No se permite consumir vales no vigentes (RN-07).
**Criterios de aceptación:**
- Un vale agotado, anulado o vencido se rechaza con un mensaje que indica el motivo.
- Un vale de una orden anulada se rechaza (RN-13).

#### RF-CON-05. Validación de la cantidad
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema valida la cantidad ingresada.
**Criterios de aceptación:**
- La cantidad es numérica, mayor que cero y con hasta 2 decimales.
- Los errores se muestran junto al campo, en lenguaje simple.

#### RF-CON-06. Datos complementarios
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se pueden registrar datos del despacho.
**Criterios de aceptación:**
- Placa del vehículo, conductor y observación son campos opcionales; su obligatoriedad se define en P-06.
- Los datos quedan visibles en el historial del vale.

#### RF-CON-07. Fecha y hora automáticas
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema fija cuándo ocurrió el consumo.
**Criterios de aceptación:**
- Se usa la fecha y hora del servidor, en la zona horaria de Lima, y el usuario no puede modificarlas.
- El registro retroactivo solo lo hace el administrador, con motivo (ver P-09).

#### RF-CON-08. Control de concurrencia
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Dos consumos simultáneos sobre el mismo vale no corrompen el saldo (RN-06).
**Criterios de aceptación:**
- Las operaciones simultáneas se procesan una tras otra.
- El saldo nunca queda negativo y no se pierde ningún consumo.
- Con un vale de 100 galones y 10 consumos simultáneos de 15, se aceptan exactamente 6 y el saldo final es 10.

#### RF-CON-09. Prevención de doble envío
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Un doble clic o un reenvío accidental no duplica el consumo.
**Criterios de aceptación:**
- Tras confirmar, el botón queda bloqueado hasta recibir respuesta.
- Un reenvío de la misma operación no genera un segundo movimiento y devuelve el resultado del primero.

#### RF-CON-10. Confirmación y comprobante
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** El sistema confirma el consumo y entrega un comprobante.
**Criterios de aceptación:**
- Se muestra el saldo actualizado.
- Se puede imprimir o descargar un comprobante con código, cantidad, saldo y fecha.

#### RF-CON-11. Reversión de consumo
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador corrige un consumo registrado por error.
**Criterios de aceptación:**
- Exige un motivo (RN-09).
- Se registra un movimiento inverso; el consumo original permanece visible.
- El saldo se recalcula y la reversión queda auditada.
- Un consumo ya revertido no puede revertirse otra vez.

#### RF-CON-12. Historial de movimientos del vale
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Oficina y Administrador consultan la línea de tiempo completa del vale; Despachador solo recibe el resultado de su operación y el saldo necesario para despachar.
**Criterios de aceptación:**
- Lista en orden cronológico la emisión, los consumos, las anulaciones, las reversiones y los ajustes.
- Cada línea muestra cantidad, saldo posterior, usuario, fecha y motivo.

#### RF-CON-14. Sincronización de saldos entre estaciones
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Consulta rápida
**Descripción:** Los consumos y saldos se comparten entre todas las estaciones mediante una fuente de datos común.
**Criterios de aceptación:**
- Tras confirmar un consumo, la API devuelve el saldo actualizado y el cambio queda visible desde las demás estaciones en tiempo real mediante una notificación del sistema o en pocos segundos, seguida de una consulta que confirma el saldo.
- Consumos concurrentes no pueden exceder el saldo: el backend serializa las operaciones o rechaza la que ya no tenga saldo disponible.
- Un timeout/reintento no duplica una operación identificada con la misma clave de idempotencia.
- Cada movimiento registra e identifica la estación donde se realizó.

#### RF-CON-13. Coincidencia de combustible
**Prioridad:** Media · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El combustible despachado debe corresponder al del vale (ver P-03).
**Criterios de aceptación:**
- Si el vale define un tipo de combustible, el consumo se registra con ese tipo.
- Una discrepancia se rechaza con un mensaje claro.

[↑ Volver al índice](#indice)

---

<a id="m09"></a>

### M09. Consultas de saldo y consumo

Consultas rápidas para responder "cuánto saldo queda" y "cuánto se consumió".

#### RF-QRY-01. Búsqueda rápida de saldo por código
**Prioridad:** Alta · **Actor:** Todos los roles autenticados · **Objetivo:** Consulta rápida
**Descripción:** Un buscador accesible desde cualquier pantalla devuelve el saldo de un vale por su código interno o por el número de la entidad.
**Criterios de aceptación:**
- Al ingresar un código se muestran saldo, estado e institución en un solo paso.
- Sugiere coincidencias mientras se escribe.
- Si el número coincide con varios vales, lista institución, orden y combustible para elegir.

#### RF-QRY-02. Saldo por orden de compra
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consulta el estado de una orden.
**Criterios de aceptación:**
- Muestra presupuesto en soles, total emitido (en galones y en soles), total consumido en galones, saldo en galones de cada vale y saldo total.
- Muestra el presupuesto restante por emitir.

#### RF-QRY-03. Saldo por institución
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consulta el saldo consolidado de una institución.
**Criterios de aceptación:**
- Muestra el saldo vigente total con desglose por orden y por vale.
- Excluye del saldo vigente los vales anulados y vencidos, y los muestra aparte.

#### RF-QRY-04. Consumo por institución y periodo
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consulta cuánto consumió una institución.
**Criterios de aceptación:**
- Filtro por rango de fechas y agrupación diaria, semanal o mensual.
- Muestra el total y el detalle por periodo.
- Las reversiones se descuentan del consumo.

#### RF-QRY-05. Consumo por orden y por vale
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se consulta el detalle de consumos de una orden o de un vale.
**Criterios de aceptación:**
- Lista cada consumo con fecha, cantidad, saldo posterior y usuario.
- Permite filtrar por rango de fechas.

#### RF-QRY-06. Filtros combinables
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Las consultas admiten varios filtros a la vez.
**Criterios de aceptación:**
- Se combinan combustible, estado, emisor y rango de fechas.
- Un botón limpia todos los filtros.
- Los filtros activos quedan en la dirección de la página.

#### RF-QRY-07. Estado de cuenta de institución
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Se genera el estado de cuenta de una institución en un periodo.
**Criterios de aceptación:**
- Muestra saldo inicial, movimientos cronológicos, consumos y saldo final del periodo.
- Saldo inicial más movimientos es igual al saldo final.

#### RF-QRY-08. Saldo siempre actualizado
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** Las consultas reflejan el último movimiento registrado.
**Criterios de aceptación:**
- Ninguna consulta muestra un saldo desactualizado: tras registrar un consumo, la siguiente consulta ya lo refleja.

[↑ Volver al índice](#indice)

---

<a id="m10"></a>

### M10. Reportes, gráficos y exportación

Visualización agregada del consumo y salida de datos hacia Excel y PDF.

#### RF-REP-01. Panel de inicio
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Pantalla de bienvenida con indicadores del periodo actual.
**Criterios de aceptación:**
- Muestra órdenes del mes, vales activos, galones consumidos en el mes y vales por agotarse o vencer (RF-VAL-13).
- Cada indicador enlaza al listado correspondiente.
- El administrador ve además un aviso si hay diferencias de saldo sin revisar (RF-AUD-06).

#### RF-REP-02. Gráfico de consumo por periodo
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Gráfico del consumo agrupado en el tiempo.
**Criterios de aceptación:**
- Barras o líneas con agrupación diaria, semanal o mensual.
- Se actualiza al cambiar los filtros sin recargar la página.
- Ofrece los mismos datos en forma de tabla.

#### RF-REP-03. Gráfico de consumo por institución
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Ranking de instituciones por consumo.
**Criterios de aceptación:**
- Muestra las instituciones con mayor consumo en el periodo elegido.
- Ofrece los mismos datos en forma de tabla.

#### RF-REP-04. Gráfico de consumo por combustible
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Distribución del consumo por tipo de combustible.
**Criterios de aceptación:**
- Muestra el consumo por tipo de combustible en el periodo elegido.
- Ofrece los mismos datos en forma de tabla.

#### RF-REP-05. Reporte de órdenes por periodo
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Resumen de las órdenes registradas.
**Criterios de aceptación:**
- Muestra la cantidad de órdenes y el presupuesto total del periodo.
- Incluye el detalle por institución.

#### RF-REP-06. Filtros de fecha predefinidos
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Consulta rápida
**Descripción:** Atajos para elegir periodos en consultas y reportes.
**Criterios de aceptación:**
- Opciones: hoy, esta semana, este mes, mes anterior y rango personalizado.
- La zona horaria es la de Lima.

#### RF-REP-07. Exportación a Excel
**Prioridad:** Alta · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Los reportes y consultas se exportan a Excel.
**Criterios de aceptación:**
- Genera un archivo .xlsx con los filtros aplicados y encabezados claros.
- Los datos exportados coinciden con los mostrados en pantalla.

#### RF-REP-08. Exportación a PDF
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Los reportes y el estado de cuenta se exportan a PDF.
**Criterios de aceptación:**
- El PDF incluye los datos de la estación, la fecha de emisión y los filtros usados.
- Los datos exportados coinciden con los mostrados en pantalla.

[↑ Volver al índice](#indice)

---

<a id="m11"></a>

### M11. Auditoría e integridad de saldos

Trazabilidad de las acciones y verificación automática de que los saldos son correctos.

#### RF-AUD-01. Registro de acciones
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Soporte
**Descripción:** El sistema deja huella de las acciones sensibles.
**Criterios de aceptación:**
- Registra inicios de sesión, altas, ediciones, anulaciones, ajustes, reversiones, cambios de precio y de parámetros, con usuario, fecha y hora, entidad afectada y valores anteriores y nuevos.
- Cada consumo queda registrado como movimiento con su usuario y fecha.

#### RF-AUD-02. Bitácora inalterable
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** La bitácora y los movimientos de vales no se pueden modificar (RN-11).
**Criterios de aceptación:**
- Ninguna pantalla permite editar o eliminar registros de auditoría.
- Un intento de modificar o borrar un movimiento de vale, incluso directamente en la base de datos, es rechazado.

#### RF-AUD-03. Consulta de bitácora
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador revisa las acciones registradas.
**Criterios de aceptación:**
- Filtros por usuario, acción, entidad y fecha.
- Cada registro muestra los valores anteriores y nuevos.
- Listado paginado.

#### RF-AUD-04. Historial por registro
**Prioridad:** Media · **Actor:** Oficina, Administrador · **Objetivo:** Soporte
**Descripción:** Se ve la línea de cambios de una orden o de un vale.
**Criterios de aceptación:**
- Desde el detalle de la orden o del vale se muestran los cambios con usuario y fecha.

#### RF-AUD-05. Verificación de integridad de saldos
**Prioridad:** Alta · **Actor:** Sistema · **Objetivo:** Saldos exactos
**Descripción:** El sistema comprueba que los saldos coincidan con los movimientos (RN-08).
**Criterios de aceptación:**
- Un proceso diario recalcula el saldo de cada vale a partir de sus movimientos y lo compara con el saldo almacenado.
- Registra el resultado (fecha, vales revisados, diferencias).
- El proceso puede ejecutarse también a demanda y señala con un código de error si hay diferencias.

#### RF-AUD-06. Alerta de diferencias
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Saldos exactos
**Descripción:** El administrador es avisado si hay diferencias.
**Criterios de aceptación:**
- Se muestra el detalle (vale, saldo almacenado, saldo recalculado).
- Cada diferencia se puede marcar como revisada con un comentario.
- Una diferencia revisada no vuelve a avisarse salvo que reaparezca.

[↑ Volver al índice](#indice)

---

<a id="m12"></a>

### M12. Configuración del sistema

Parámetros que el administrador ajusta sin modificar el código.

#### RF-CFG-01. Parámetros del sistema
**Prioridad:** Media · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador ajusta los valores de funcionamiento del sistema.
**Criterios de aceptación:**
- Permite configurar: umbral de confianza del OCR, tamaño máximo de archivo, formato del código de vale, vigencia por defecto del vale, umbral de saldo bajo, días de aviso por vencimiento, tiempo de inactividad de sesión, intentos de inicio de sesión permitidos y tiempo de bloqueo.
- Cada parámetro se valida (tipo y rango) antes de guardarse y muestra el efecto del cambio.
- Los cambios rigen sin reiniciar el sistema y quedan auditados.

#### RF-CFG-02. Datos de la estación
**Prioridad:** Baja · **Actor:** Administrador · **Objetivo:** Soporte
**Descripción:** El administrador registra los datos de la estación.
**Criterios de aceptación:**
- Nombre, RUC, dirección y logo.
- Se usan en comprobantes, vales impresos, PDF y reportes.

[↑ Volver al índice](#indice)

---

<a id="resumen"></a>

## 6. Resumen de requerimientos

- **M01. Autenticación y sesión:** 10 requerimientos (Alta 6, Media 4, Baja 0)
- **M02. Usuarios, roles y permisos:** 7 requerimientos (Alta 4, Media 3, Baja 0)
- **M03. Instituciones:** 5 requerimientos (Alta 3, Media 2, Baja 0)
- **M04. Combustibles y precios:** 4 requerimientos (Alta 3, Media 1, Baja 0)
- **M05. Órdenes de compra:** 11 requerimientos (Alta 8, Media 3, Baja 0)
- **M06. Lectura de órdenes con OCR:** 13 requerimientos (Alta 9, Media 3, Baja 1)
- **M07. Vales de combustible:** 15 requerimientos (Alta 9, Media 5, Baja 1)
- **M08. Consumos:** 14 requerimientos (Alta 10, Media 4, Baja 0)
- **M09. Despachador de saldo y consumo:** 8 requerimientos (Alta 6, Media 2, Baja 0)
- **M10. Reportes, gráficos y exportación:** 8 requerimientos (Alta 2, Media 6, Baja 0)
- **M11. Auditoría e integridad de saldos:** 6 requerimientos (Alta 3, Media 3, Baja 0)
- **M12. Configuración del sistema:** 2 requerimientos (Alta 0, Media 1, Baja 1)
- **Total:** 103 requerimientos (Alta 63, Media 37, Baja 3)

[↑ Volver al índice](#indice)

---

<a id="trazabilidad"></a>

## 7. Trazabilidad con los objetivos del sistema

Cada requerimiento contribuye a uno de los objetivos del sistema (sección 1.2). Esta sección los agrupa.

- **Registro ágil** (Registrar órdenes de compra en menos tiempo y con menos errores de digitación), 11 requerimientos: INS-01, ORD-01, ORD-03, OCR-01, OCR-02, OCR-03, OCR-05, OCR-08, OCR-09, VAL-01, VAL-04.
- **Saldos exactos** (Que el saldo de cada vale sea siempre el correcto), 31 requerimientos: CMB-02, CMB-04, ORD-02, ORD-07, ORD-09, ORD-11, OCR-04, OCR-06, OCR-07, VAL-02, VAL-03, VAL-05, VAL-08, VAL-10, VAL-11, VAL-14, VAL-15, CON-01, CON-02, CON-03, CON-04, CON-05, CON-07, CON-08, CON-09, CON-11, CON-13, QRY-08, AUD-02, AUD-05, AUD-06.
- **Consulta rápida** (Consultar saldo y consumo de forma inmediata), 17 requerimientos: INS-03, INS-04, ORD-05, ORD-06, VAL-06, VAL-07, CON-12, QRY-01, QRY-02, QRY-03, QRY-04, QRY-05, QRY-06, QRY-07, REP-02, REP-03, REP-06.
- **Soporte** (Hacen posible el sistema: acceso, auditoría, configuración y reportes), 42 requerimientos: AUT-01, AUT-02, AUT-03, AUT-04, AUT-05, AUT-06, AUT-07, AUT-08, AUT-09, USR-01, USR-02, USR-03, USR-04, USR-05, USR-06, USR-07, INS-02, INS-05, CMB-01, CMB-03, ORD-04, ORD-08, ORD-10, OCR-10, OCR-11, OCR-12, OCR-13, VAL-09, VAL-12, VAL-13, CON-06, CON-10, REP-01, REP-04, REP-05, REP-07, REP-08, AUD-01, AUD-03, AUD-04, CFG-01, CFG-02.

[↑ Volver al índice](#indice)

---

<a id="pendientes"></a>

## 8. Decisiones confirmadas y puntos por confirmar

<a id="decisiones"></a>

### 8.1 Decisiones confirmadas

- **D-01.** El presupuesto de la orden está en soles y los vales en galones. Como el precio del combustible varía, la conversión se hace con el precio actual del combustible. *Requerimientos afectados:* ORD-01, ORD-06, CMB-02, CMB-04, VAL-01, VAL-03, QRY-02, RN-03, RN-16.
- **D-02.** Los vales generados por las entidades se vinculan a una orden. Algunas entidades usan numeración general y otras generan vales solo para cada orden, y esa numeración se acaba. *Requerimientos afectados:* INS-01, VAL-02, VAL-05, VAL-06, VAL-15, CON-01, QRY-01, RN-14, RN-15.

<a id="puntos"></a>

### 8.2 Puntos por confirmar

Decisiones que deben validarse con la estación de servicio antes de cerrar el diseño. Cada una puede cambiar uno o más requerimientos. Se indica entre paréntesis el supuesto con el que se avanza mientras tanto. La numeración se conserva respecto de las versiones anteriores del proyecto; P-07 se retiró porque pertenecía a la tesis y no al sistema.

- **P-01. Impresión de vales.** ¿Los vales de la estación se imprimen? ¿Con qué formato y con QR, código de barras o solo número? (Supuesto: se imprimen con QR.) *Afecta:* VAL-12.
- **P-02. Vencimiento de vales.** ¿Los vales vencen? ¿Cuál es la vigencia habitual? (Supuesto: la fecha de vencimiento es opcional.) *Afecta:* VAL-01, VAL-09, CFG-01.
- **P-03. Combustible del consumo.** ¿Cada vale es de un solo tipo de combustible? ¿Puede consumirse otro distinto? (Supuesto: debe coincidir.) *Afecta:* CON-13.
- **P-04. Anulación de órdenes con consumos.** ¿Qué debe pasar si se quiere anular una orden que ya tiene consumos? (Supuesto: no se permite; solo se cierra.) *Afecta:* ORD-09, RN-17.
- **P-05. Campos reales de las órdenes.** Campos exactos de las órdenes de compra que entregan las instituciones. Define qué extrae el OCR y qué campos son obligatorios. *Afecta:* OCR-03, OCR-06.
- **P-06. Datos del consumo.** ¿La placa del vehículo y el conductor son obligatorios? ¿Se necesita firma o conformidad de la institución? (Supuesto: opcionales.) *Afecta:* CON-06.
- **P-08. Correo saliente.** ¿La estación cuenta con una cuenta de correo para enviar mensajes del sistema? Es necesaria para recuperar contraseñas. *Afecta:* AUT-05.
- **P-09. Registro retroactivo de consumos.** ¿Se permite registrar consumos con fecha pasada (por ejemplo, un despacho anotado a mano que se carga después)? (Supuesto: solo el administrador, con motivo.) *Afecta:* CON-07.
- **P-10. Precio fijo al emitir.** ¿El precio por galón queda fijo en el vale al emitirlo, o el valor en soles debe recalcularse cuando cambia el precio? (Supuesto: queda fijo.) *Afecta:* CMB-02, VAL-01, VAL-03, RN-16.
- **P-11. Vales de entidad y presupuesto.** ¿Los vales de entidad descuentan del presupuesto de la orden al registrarse? ¿Con qué precio (el de la fecha del vale o el del registro)? ¿Se registran por adelantado o cuando se presentan para consumir? (Supuesto: descuentan, con el precio vigente al registrarlos.) *Afecta:* VAL-05, VAL-03.
- **P-12. Rango de numeración.** Para numeración por orden: ¿la orden indica el rango de números autorizado, desde y hasta? ¿Qué debe pasar cuando el rango se agota? (Supuesto: el rango es opcional y, si existe, se controla.) *Afecta:* ORD-01, VAL-15.
- **P-13. Liberación de presupuesto al anular vales.** Al anular un vale con consumo parcial, ¿se libera solo la parte no consumida? (Supuesto: sí.) *Afecta:* VAL-03, VAL-10, RN-18.

[↑ Volver al índice](#indice)

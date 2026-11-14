# REQUERIMIENTOS FUNCIONALES DEL SISTEMA

**Proyecto:** Sistema de control de órdenes de compra y vales de combustible  
**Entidad:** Estación de Servicio San José  
**Sedes identificadas:** San José y Santa Marta  
**Documento:** Requerimientos funcionales  
**Fuente:** Documento de levantamiento de requisitos de la Estación de Servicio San José  
**Versión:** 2.0

---

## 1. Información general

### 1.1. Nombre del proyecto

Sistema de control de órdenes de compra y vales de combustible de la Estación de Servicio San José.

### 1.2. Descripción del sistema

La Estación de Servicio San José se dedica a la venta y despacho de combustibles y cuenta con dos sedes: San José y Santa Marta. El sistema permitirá controlar las órdenes de compra emitidas por instituciones o entidades, los vales físicos que presentan sus clientes y los despachos realizados por los griferos.

El flujo operativo inicia cuando el personal de oficina registra una orden de compra. Posteriormente, el cliente se presenta en cualquiera de las sedes con un vale de combustible. Antes de despachar, el grifero consulta la orden y verifica que tenga saldo suficiente. Luego registra el vale presentado y la cantidad realmente despachada. El vale puede ser atendido parcialmente: por ejemplo, si autoriza 10 galones y el cliente recibe 5, el sistema registra 5 galones atendidos y mantiene 5 galones disponibles en ese mismo vale.

Después de la atención, el vale físico es enviado a la oficina. El personal de oficina no vuelve a registrar el vale; verifica que la información capturada por el grifero coincida con el documento físico. El sistema calcula los saldos y estados automáticamente y comparte la información entre ambas sedes.

### 1.3. Objetivo del sistema

Reducir el tiempo empleado en el registro y control de las órdenes de compra y los vales de combustible, disminuir los errores de contabilización y permitir que los trabajadores consulten los saldos actualizados antes de atender un vale.

El sistema deberá evitar que se despache una cantidad de combustible superior al saldo disponible de la orden de compra o del vale correspondiente.

### 1.4. Alcance funcional

El sistema contempla las siguientes funcionalidades:

- Administración de usuarios mediante los roles Administrador, Oficina y Grifero, con permisos predefinidos por rol.
- Registro de órdenes de compra por el personal de oficina, con apoyo de OCR para extraer información de archivos PDF.
- Consulta, búsqueda, modificación y eliminación condicionada de órdenes de compra.
- Registro del vale en el momento de su primera atención por el grifero, sin pre-registro por parte de Oficina.
- Registro de uno o varios despachos parciales vinculados al mismo vale.
- Consulta previa del saldo de la orden de compra y, cuando corresponda, del saldo restante del vale.
- Verificación posterior por parte de Oficina de los datos capturados por el grifero contra el vale físico.
- Cálculo automático de saldos y estados de órdenes y vales.
- Consulta compartida de saldos entre San José y Santa Marta.
- Consulta de registros históricos del sistema.
- Reportes por horas, días, semanas y meses, con filtros por fecha, usuario y estado.
- Panel principal con gráficos interactivos.
- Exportación de reportes a PDF y Excel.

No se contempla la migración de los registros actuales de Excel o PDF al nuevo sistema. Tampoco se identificó la necesidad de integrarse con sistemas externos, plataformas de pago, correo electrónico, WhatsApp o sistemas gubernamentales. La impresión directa de reportes y la comparación de períodos no forman parte del alcance actualizado.

---

## 2. Actores del sistema

| **ID** | **Actor** | **Descripción** | **Responsabilidades** |
|---|---|---|---|
| ACT-001 | Administrador | Propietario y responsable del sistema. | Crear usuarios, asignarles un rol, habilitar o deshabilitar cuentas, acceder a todos los módulos y supervisar las atenciones registradas por los griferos. |
| ACT-002 | Personal de oficina | Trabajadores responsables de la gestión administrativa de las órdenes y la revisión de vales atendidos. | Registrar y mantener órdenes de compra, revisar la información de los vales capturados por los griferos, verificar los documentos físicos, consultar saldos y generar/exportar reportes. |
| ACT-003 | Grifero | Trabajador responsable de atender a los clientes y despachar combustible. | Consultar órdenes y saldos antes del despacho, capturar los datos del vale presentado al momento de la primera atención, registrar los galones realmente despachados y consultar el saldo restante del vale. |

### 2.1. Consideraciones sobre los usuarios

- En el levantamiento se indicó un aproximado de ocho usuarios: un administrador, tres trabajadores de oficina y cuatro griferos.
- En la descripción general del negocio se indicó que actualmente trabajan seis personas, mientras que el levantamiento estima ocho cuentas (un administrador, tres de oficina y cuatro griferos). La diferencia se mantiene como dato administrativo pendiente de confirmación.
- No se identificaron usuarios externos que deban acceder al sistema.
- Los usuarios no tendrán las mismas funcionalidades; el acceso estará determinado por sus roles.

---

## 3. Módulos del sistema

### MOD-001. Administración de usuarios y acceso

**Descripción:** Permite al administrador registrar usuarios, asignarles uno de los roles predefinidos y habilitar o deshabilitar sus cuentas.

**Objetivo:** Controlar el acceso a los módulos de acuerdo con el rol de cada usuario y conservar la relación histórica entre usuarios y operaciones.

**Actores involucrados:** Administrador.

**Funcionalidades principales:** registro de usuarios, asignación de roles, permisos predefinidos por rol, habilitación/deshabilitación de cuentas e inicio/cierre de sesión.

### MOD-002. Gestión de órdenes de compra

**Descripción:** Permite registrar las órdenes recibidas de instituciones o entidades, con apoyo de extracción OCR desde documentos PDF.

**Objetivo:** Mantener la información de las órdenes y el total autorizado por tipo de combustible para controlar los despachos.

**Actores involucrados:** Administrador y personal de oficina.

**Funcionalidades principales:** registro asistido por OCR, revisión de datos extraídos, consulta, búsqueda, filtros, paginación, ordenación, modificación y eliminación condicionada de órdenes.

### MOD-003. Atención de vales y verificación administrativa

**Descripción:** Permite que el grifero capture los datos del vale físico en el momento de atenderlo y registre la cantidad realmente despachada. El vale no requiere un registro previo por Oficina. Posteriormente, Oficina verifica que los datos capturados coincidan con el documento físico recibido.

**Objetivo:** Evitar el doble registro, mantener el historial de despachos y controlar los saldos parciales de cada vale.

**Actores involucrados:** Grifero, personal de oficina y Administrador.

**Funcionalidades principales:** captura del vale durante la primera atención, registro de despachos parciales, consulta por número de vale, orden o entidad, modificación de datos descriptivos permitidos, verificación administrativa y protección de registros atendidos frente a eliminación.

### MOD-004. Control de saldos y estados

**Descripción:** Calcula automáticamente los saldos de órdenes y vales a partir de los galones efectivamente despachados.

**Objetivo:** Impedir despachos que excedan el saldo disponible y mostrar información consistente a los usuarios de ambas sedes.

**Actores involucrados:** Sistema, Administrador, personal de oficina y griferos.

**Funcionalidades principales:** consulta previa de saldo, cálculo de saldos, actualización transaccional después de cada despacho, actualización automática de estados y consulta compartida entre sedes.

### MOD-005. Reportes y panel principal

**Descripción:** Permite consultar órdenes, saldos y vales atendidos mediante reportes y gráficos interactivos.

**Objetivo:** Facilitar el control administrativo de las operaciones.

**Actores involucrados:** Administrador y personal de oficina.

**Funcionalidades principales:** reportes de órdenes y atenciones por horas, días, semanas y meses; filtros por fecha, usuario y estado; dashboard y exportación a PDF y Excel. No incluye comparación de períodos ni impresión directa.

### MOD-006. OCR para órdenes de compra

**Descripción:** Procesa exclusivamente archivos PDF de órdenes de compra para extraer sus datos y completar los campos del formulario de registro.

**Objetivo:** Reducir la digitación manual y acelerar el registro, manteniendo la revisión humana antes de guardar la orden.

**Actores involucrados:** Personal de oficina y Administrador, según sus permisos de gestión de órdenes.

**Funcionalidades principales:** carga temporal del PDF, extracción mediante RapidOCR, prellenado del formulario, revisión y corrección manual de los campos extraídos. El OCR no registra la orden automáticamente ni procesa vales.

---

## 4. Requerimientos funcionales

> **Criterio de redacción:** Los requerimientos siguientes se basan en las respuestas del levantamiento. Cuando una operación depende de una definición que todavía no existe, se indica expresamente en la sección de información pendiente.

## 4.1. Administración de usuarios y acceso

### RF-001: Registrar usuarios del sistema

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Administrador.

**Descripción:**

El sistema deberá permitir que el administrador registre nuevos usuarios proporcionando nombres, apellidos, DNI, correo electrónico, contraseña inicial y rol.

**Precondiciones:**

- El administrador debe tener acceso al sistema.
- El usuario que se desea registrar no debe estar registrado previamente, sujeto a la definición de duplicidad de cuentas.

**Flujo principal:**

1. El administrador accede a la administración de usuarios.
2. Selecciona la opción para registrar un usuario.
3. Ingresa nombres, apellidos, DNI, correo electrónico, contraseña inicial y rol.
4. El sistema verifica que se hayan proporcionado los datos requeridos.
5. El sistema registra al usuario y le asigna el rol seleccionado.
6. El sistema informa que el registro se realizó.

**Flujos alternativos y excepciones:**

- Si falta alguno de los datos requeridos, el sistema no deberá completar el registro.
- El mecanismo para detectar usuarios duplicados debe definirse.

**Datos de entrada:** Nombres, apellidos, DNI, correo electrónico, contraseña inicial y rol.

**Resultados esperados:** Usuario registrado con el rol asignado.

**Reglas de negocio relacionadas:** RN-009, RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado que el administrador ha ingresado todos los datos requeridos, cuando confirma el registro, entonces el sistema crea el usuario con el rol seleccionado.
- Dado que falta un dato requerido, cuando el administrador intenta registrar el usuario, entonces el sistema no completa el registro.

### RF-002: Asignar roles y restringir funcionalidades

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Administrador.

**Descripción:**

El sistema deberá permitir que el administrador asigne a cada usuario uno de los roles predefinidos —Administrador, Oficina o Grifero—. Cada rol tendrá un conjunto de permisos establecido por el sistema; al iniciar sesión, el usuario verá únicamente los módulos y acciones permitidos para su rol. El administrador tendrá acceso a todos los módulos. La autorización efectiva deberá comprobarse también en el servidor, no solo ocultando opciones en la interfaz.

**Precondiciones:**

- El usuario debe encontrarse registrado.
- El rol que se asignará debe ser uno de los tres roles identificados.

**Flujo principal:**

1. El administrador registra un usuario o gestiona sus datos.
2. Selecciona el rol correspondiente.
3. El sistema relaciona el usuario con el rol.
4. Cuando el usuario accede a una funcionalidad, el sistema verifica los permisos asociados a su rol.
5. El sistema permite o deniega el acceso según los permisos definidos.

**Flujos alternativos y excepciones:**

- Si un usuario intenta ejecutar una operación para la que no tiene autorización, el sistema deberá impedirla.
- Los permisos que no estén especificados deberán permanecer pendientes de definición.

**Datos de entrada:** Usuario y rol asignado.

**Resultados esperados:** Acceso limitado a las funcionalidades que corresponden al rol.

**Reglas de negocio relacionadas:** RN-009, RN-010, RN-011.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un usuario con rol Grifero, cuando intenta acceder a una funcionalidad restringida para ese rol, entonces el sistema deniega el acceso.
- Dado un usuario con rol Administrador, cuando accede a un módulo, entonces el sistema permite el acceso conforme a la indicación de que este rol tiene acceso a todos los módulos.

### RF-003: Iniciar sesión en el sistema

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Usuario registrado.

**Descripción:**

El sistema deberá permitir que los usuarios registrados accedan a sus funcionalidades mediante las credenciales de su cuenta, de modo que puedan utilizar únicamente las opciones autorizadas para su rol. La información recopilada contempla correo electrónico y contraseña como datos de la cuenta; los detalles adicionales del mecanismo de autenticación deben confirmarse.

**Precondiciones:**

- El usuario debe estar registrado.
- La cuenta debe encontrarse habilitada para el acceso.

**Flujo principal:**

1. El usuario ingresa sus credenciales.
2. El sistema verifica la información proporcionada.
3. El sistema identifica el rol del usuario.
4. El sistema permite el acceso a las funcionalidades correspondientes.

**Flujos alternativos y excepciones:**

- Si las credenciales no son válidas, el sistema no deberá permitir el acceso.
- Las reglas de recuperación, cambio de contraseña y habilitación de cuentas están pendientes de definición.

**Datos de entrada:** Correo electrónico y contraseña.

**Resultados esperados:** Acceso a las funcionalidades permitidas para el usuario.

**Reglas de negocio relacionadas:** RN-009, RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un usuario registrado con credenciales válidas, cuando intenta iniciar sesión, entonces el sistema le permite acceder según su rol.
- Dado un usuario que proporciona credenciales no válidas, cuando intenta iniciar sesión, entonces el sistema deniega el acceso.

### RF-004: Deshabilitar y habilitar usuarios sin eliminar sus registros

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Administrador.

**Descripción:**

El sistema deberá permitir que el administrador deshabilite una cuenta cuando un trabajador deje de utilizar el sistema y, si corresponde, vuelva a habilitarla. No se eliminará físicamente al usuario, porque sus datos deben continuar asociados a las órdenes, verificaciones y despachos históricos que haya realizado.

**Precondiciones:** El usuario objetivo debe existir y el administrador debe estar autorizado para administrar cuentas.

**Flujo principal:**

1. El administrador consulta el listado de usuarios.
2. Selecciona una cuenta y elige habilitarla o deshabilitarla.
3. El sistema solicita confirmación.
4. El administrador confirma.
5. El sistema actualiza el estado de la cuenta y, cuando se deshabilita, impide nuevos inicios de sesión y revoca sus sesiones activas.
6. El sistema conserva los registros históricos vinculados al usuario.

**Flujos alternativos y excepciones:**

- Si el administrador cancela la confirmación, la cuenta permanece sin cambios.
- El sistema no deberá permitir deshabilitar al último administrador activo, para evitar dejar el sistema sin administración.

**Datos de entrada:** Usuario seleccionado, acción (habilitar/deshabilitar) y confirmación.

**Resultados esperados:** Cuenta habilitada o deshabilitada; los registros históricos y sus relaciones permanecen intactos.

**Reglas de negocio relacionadas:** RN-010, RN-014, RN-015.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un usuario activo, cuando el administrador confirma su deshabilitación, entonces el usuario no puede iniciar nuevas sesiones y sus registros históricos se conservan.
- Dado un usuario deshabilitado, cuando el administrador confirma su habilitación, entonces puede volver a iniciar sesión con sus credenciales vigentes.
- Dada una cuenta que tiene órdenes o atenciones asociadas, cuando se deshabilita, entonces esas relaciones no se eliminan.

### RF-005: Cerrar sesión

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Usuario autenticado.

**Descripción:**

El sistema deberá permitir cerrar una sesión de usuario, conforme a la necesidad de cierre de sesiones identificada en el levantamiento.

**Precondiciones:** El usuario debe tener una sesión iniciada.

**Flujo principal:**

1. El usuario selecciona la opción de cerrar sesión.
2. El sistema finaliza la sesión.
3. El sistema deja de mostrar las funcionalidades protegidas de esa sesión.

**Flujos alternativos y excepciones:** No se especificaron situaciones alternativas.

**Datos de entrada:** Solicitud de cierre de sesión.

**Resultados esperados:** Sesión finalizada.

**Reglas de negocio relacionadas:** RN-010.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado un usuario con sesión iniciada, cuando selecciona cerrar sesión, entonces el sistema finaliza su sesión.

### RF-006: Consultar los registros de atención realizados por los griferos

**Módulo:** MOD-001. Administración de usuarios y acceso.  
**Actor principal:** Administrador.

**Descripción:**

El sistema deberá permitir que el administrador consulte los registros de atención de vales realizados por los griferos, de manera que pueda revisar las operaciones que estos registran.

**Precondiciones:** Deben existir registros de atención de vales realizados por griferos.

**Flujo principal:**

1. El administrador accede a la consulta de atenciones.
2. El sistema presenta los registros disponibles.
3. El administrador consulta la información de las atenciones.

**Flujos alternativos y excepciones:** No se indicó que deba existir una auditoría completa de todas las acciones de todos los roles. El alcance confirmado se limita a poder visualizar las acciones o registros realizados por los griferos.

**Datos de entrada:** Criterios de consulta, si se definen.

**Resultados esperados:** El administrador visualiza los registros de atención realizados por los griferos.

**Reglas de negocio relacionadas:** RN-012.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado que existen atenciones registradas por griferos, cuando el administrador consulta estos registros, entonces el sistema muestra las atenciones disponibles.

## 4.2. Gestión de órdenes de compra

### RF-007: Registrar órdenes de compra con apoyo de OCR

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina.

**Descripción:**

El sistema deberá permitir que el personal de oficina registre una orden de compra mediante un formulario cuyos datos podrán ingresarse manualmente o completarse con el resultado del procesamiento OCR descrito en RF-034. En ambos casos, el trabajador deberá revisar y confirmar los datos antes de guardar la orden.

**Precondiciones:**

- El usuario debe tener permisos de gestión de órdenes.
- Debe disponer de los datos de la orden o de su archivo PDF.

**Flujo principal:**

1. El trabajador abre el formulario de nueva orden.
2. Ingresa los datos manualmente o solicita el autocompletado mediante RF-034.
3. El sistema presenta el formulario con los datos ingresados o extraídos.
4. El trabajador revisa y corrige todos los campos.
5. El sistema valida los campos obligatorios y la consistencia de cantidades e importes.
6. El trabajador confirma el registro y el sistema guarda la orden.

**Flujos alternativos y excepciones:**

- Si el procesamiento OCR falla, el trabajador podrá continuar con el registro manual conforme a RF-034.
- Si faltan datos obligatorios, el registro no se completa.
- La orden no se guarda hasta que el trabajador revise y confirme el formulario.

**Datos de entrada:** Número de orden, expediente SIAF, fecha, proveedor, unidad ejecutora, RUC de la unidad ejecutora y una o más líneas de combustible con cantidad, descripción/tipo, precio unitario y precio total. Los campos pueden provenir del ingreso manual o del resultado revisado de RF-034.

**Resultados esperados:** Orden registrada con datos revisados por el trabajador y lista para recibir atenciones de vales.

**Reglas de negocio relacionadas:** RN-003, RN-021.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un formulario completo y revisado, cuando el trabajador confirma el registro, entonces el sistema guarda la orden.
- Dado que falta un campo obligatorio, cuando se intenta guardar, entonces el sistema impide el registro.
- Dado que los datos provienen del OCR, cuando el trabajador no los ha revisado y confirmado, entonces el sistema no guarda la orden.

### RF-008: Consultar el detalle de una orden de compra

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador.

**Descripción:**

El sistema deberá permitir consultar el detalle de las órdenes de compra registradas, incluyendo los datos ingresados y la información de los vales asociados.

**Precondiciones:** Debe existir al menos una orden de compra registrada.

**Flujo principal:**

1. El usuario accede al módulo de órdenes de compra.
2. Selecciona una orden de compra.
3. El sistema presenta el detalle de la orden y los vales asociados disponibles para consulta.

**Flujos alternativos y excepciones:** Si no existen órdenes registradas que correspondan a la consulta, el sistema deberá informar que no hay resultados.

**Datos de entrada:** Orden de compra seleccionada.

**Resultados esperados:** Visualización del detalle de la orden y de sus vales relacionados.

**Reglas de negocio relacionadas:** RN-002, RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden registrada, cuando el usuario autorizado consulta su detalle, entonces el sistema muestra sus datos y los vales asociados.

### RF-009: Buscar órdenes de compra

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador.

**Descripción:**

El sistema deberá permitir buscar órdenes de compra utilizando su código o número, y consultar los resultados aplicando filtros por fechas.

**Precondiciones:** Deben existir órdenes registradas para obtener resultados.

**Flujo principal:**

1. El usuario accede a la consulta de órdenes.
2. Ingresa el número o código de la orden, o selecciona un criterio de fecha.
3. El sistema realiza la búsqueda.
4. El sistema presenta las órdenes que coinciden con los criterios.
5. El usuario puede consultar el detalle de una orden.

**Flujos alternativos y excepciones:** Si no hay coincidencias, el sistema informa que no existen resultados para los criterios seleccionados.

**Datos de entrada:** Número o código de orden y fechas de consulta.

**Resultados esperados:** Listado de órdenes que cumplen los criterios de búsqueda.

**Reglas de negocio relacionadas:** RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un número de orden existente, cuando el usuario lo utiliza como criterio de búsqueda, entonces el sistema muestra la orden correspondiente.
- Dado un rango de fechas, cuando el usuario aplica el filtro, entonces el sistema muestra las órdenes correspondientes a ese período.

### RF-010: Paginar los resultados de órdenes de compra

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador.

**Descripción:**

El sistema deberá presentar los resultados de órdenes de compra mediante páginas cuando exista una cantidad elevada de registros.

**Precondiciones:** Deben existir resultados de consulta que requieran paginación.

**Flujo principal:**

1. El usuario realiza una consulta de órdenes.
2. El sistema presenta los resultados distribuidos en páginas.
3. El usuario selecciona otra página.
4. El sistema presenta los registros de la página seleccionada.

**Flujos alternativos y excepciones:** No se especificaron el tamaño de página ni las opciones de navegación.

**Datos de entrada:** Consulta realizada y página seleccionada.

**Resultados esperados:** Resultados organizados en páginas.

**Reglas de negocio relacionadas:** Ninguna identificada.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado que una consulta devuelve una cantidad de órdenes que requiere paginación, cuando el usuario navega a otra página, entonces el sistema presenta el grupo de registros correspondiente.

### RF-011: Modificar órdenes de compra

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador.

**Descripción:**

El sistema deberá permitir que el personal de oficina y el administrador modifiquen la información de una orden de compra registrada. Antes de aplicar la actualización, el sistema deberá solicitar confirmación.

**Precondiciones:**

- La orden de compra debe existir.
- El usuario debe tener permisos para modificarla.

**Flujo principal:**

1. El usuario consulta y selecciona una orden de compra.
2. Accede a la opción de modificación.
3. Actualiza los datos correspondientes.
4. El sistema solicita confirmar la actualización.
5. El usuario confirma.
6. El sistema guarda los cambios y presenta el resultado.

**Flujos alternativos y excepciones:**

- Si el usuario no confirma, el sistema no deberá aplicar los cambios.
- Si la orden ya tiene despachos, el sistema no permitirá reducir la cantidad autorizada de un combustible por debajo de los galones ya despachados ni eliminar una línea que tenga consumo asociado.
- Si una modificación afecta una línea utilizada por atenciones existentes, el sistema deberá preservar su referencia histórica.

**Datos de entrada:** Orden seleccionada, datos actualizados y confirmación.

**Resultados esperados:** Información de la orden actualizada.

**Reglas de negocio relacionadas:** RN-015, RN-016, RN-022.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden existente, cuando un usuario autorizado modifica sus datos y confirma la operación, entonces el sistema guarda la información actualizada.
- Dada una modificación pendiente de confirmación, cuando el usuario no la confirma, entonces el sistema conserva los datos anteriores.
- Dada una orden con 60 galones ya despachados de un tipo de combustible, cuando se intenta reducir su cantidad autorizada a 50, entonces el sistema rechaza la modificación.

### RF-012: Eliminar órdenes de compra sin vales asociados

**Módulo:** MOD-002. Gestión de órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador.

**Descripción:**

El sistema deberá permitir eliminar una orden de compra únicamente cuando no tenga vales ni atenciones asociadas. Si existe al menos un vale vinculado, el sistema deberá impedir la eliminación y mostrar una alerta que explique que la orden no puede eliminarse porque tiene vales asociados.

**Precondiciones:** La orden debe existir y el usuario debe tener permiso para eliminarla.

**Flujo principal:**

1. El usuario selecciona una orden de compra.
2. Solicita eliminarla.
3. El sistema comprueba si existen vales asociados.
4. Si no existen vales, el sistema solicita confirmación.
5. El usuario confirma y el sistema elimina la orden.

**Flujos alternativos y excepciones:**

- Si la orden tiene uno o más vales asociados, el sistema bloquea la operación y muestra una alerta.
- Si el usuario cancela la confirmación, la orden permanece sin cambios.
- La eliminación nunca deberá ejecutarse en cascada sobre vales o despachos.

**Datos de entrada:** Identificador de orden y confirmación de eliminación.

**Resultados esperados:** Orden eliminada solo cuando no tiene registros dependientes; de lo contrario, permanece registrada y se informa el motivo del bloqueo.

**Reglas de negocio relacionadas:** RN-014, RN-015, RN-016.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden sin vales asociados, cuando un usuario autorizado confirma la eliminación, entonces el sistema elimina la orden.
- Dada una orden con al menos un vale asociado, cuando se intenta eliminar, entonces el sistema bloquea la acción, muestra una alerta y conserva la orden y sus relaciones.

### RF-013: Verificar los datos de los vales atendidos

**Módulo:** MOD-003. Atención de vales y verificación administrativa.  
**Actor principal:** Personal de oficina.

**Descripción:**

El sistema deberá permitir que el personal de oficina revise los vales que fueron capturados por los griferos durante la atención y confirme que los datos registrados coincidan con la información del vale físico que el grifero entrega posteriormente. Oficina no deberá crear un segundo registro ni volver a digitar un vale ya capturado.

**Precondiciones:**

- Debe existir una atención registrada por un grifero.
- El vale físico correspondiente debe haber sido remitido a la oficina para su revisión.

**Flujo principal:**

1. El trabajador de oficina abre la bandeja de vales pendientes de verificación.
2. Selecciona un registro y consulta la orden, entidad, número del vale, galones autorizados, galones despachados, saldo restante, fecha y grifero responsable.
3. Compara los datos del sistema con el vale físico recibido.
4. Si coinciden, confirma la verificación.
5. El sistema registra el estado de verificación y quién la realizó y cuándo.

**Flujos alternativos y excepciones:**

- Si los datos no coinciden, el trabajador no deberá marcar el vale como verificado. El registro permanecerá pendiente y deberá seguir el procedimiento de corrección que se apruebe.
- La verificación no modifica los galones despachados ni recalcula por sí misma el saldo.
- No se crea un nuevo vale durante este proceso.

**Datos de entrada:** Vale atendido seleccionado y resultado de la comparación con el documento físico.

**Resultados esperados:** Vale marcado como verificado cuando los datos coinciden; si no coinciden, permanece pendiente de revisión.

**Reglas de negocio relacionadas:** RN-019.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un vale capturado por un grifero, cuando Oficina confirma que coincide con el documento físico, entonces el sistema lo marca como verificado.
- Dado un vale cuyos datos no coinciden, cuando Oficina intenta verificarlo, entonces el sistema no lo marca como verificado.
- Dado un vale ya capturado, cuando Oficina lo revisa, entonces el sistema no crea un segundo registro.

### RF-014: Consultar la información de órdenes y vales para la atención

**Módulo:** MOD-003 y MOD-004. Atención de vales y control de saldos.  
**Actor principal:** Grifero; Administrador y Oficina según sus permisos.

**Descripción:**

El sistema deberá permitir que el grifero localice primero una orden de compra por número o entidad/institución y consulte su saldo disponible antes de atender un vale. El vale no necesita existir previamente en el sistema: sus datos se capturan durante el primer despacho mediante RF-019. Cuando el vale ya haya sido atendido parcialmente, podrá consultarse por su número y continuar utilizando únicamente el saldo restante.

**Precondiciones:** La orden de compra debe estar registrada y el usuario debe tener permiso para consultarla.

**Flujo principal:**

1. El grifero busca la orden por número o entidad/institución.
2. El sistema muestra la orden, sus tipos de combustible y los saldos actuales.
3. El grifero verifica que exista saldo para el combustible solicitado.
4. Si el vale ya tiene una atención previa, el grifero puede localizarlo y consultar su cantidad autorizada, cantidad acumulada atendida y saldo restante.
5. El sistema presenta la información disponible sin exigir un pre-registro del vale.

**Flujos alternativos y excepciones:**

- Si la orden no existe, el sistema informa que no se encontró.
- Si el saldo de la orden es cero o insuficiente, el sistema informa que no puede realizarse el despacho solicitado.
- Si el vale todavía no existe, el usuario continúa con su captura inicial dentro del flujo de atención, no mediante un registro previo independiente.

**Datos de entrada:** Número de orden, entidad/institución y, para vales ya atendidos, número de vale.

**Resultados esperados:** Información de la orden y saldo visible antes del despacho; si existe un vale previo, también su saldo restante.

**Reglas de negocio relacionadas:** RN-001, RN-005, RN-007, RN-010, RN-011.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden registrada, cuando el grifero la busca por número o entidad, entonces visualiza sus saldos.
- Dado un vale previamente atendido de forma parcial, cuando el grifero lo consulta, entonces visualiza su saldo restante.
- Dado un vale que nunca fue atendido, cuando el grifero inicia una atención, entonces puede capturar sus datos sin que exista un registro previo.

### RF-015: Buscar órdenes y vales por número o entidad

**Módulo:** MOD-003. Atención de vales y verificación administrativa.  
**Actor principal:** Administrador, personal de oficina y grifero según sus permisos.

**Descripción:**

El sistema deberá permitir localizar vales atendidos mediante el número del vale, el número de la orden de compra o el nombre de la entidad/institución. También deberá permitir filtrar los registros por fechas. Para iniciar una atención, el grifero podrá localizar la orden por su número o entidad, aunque el vale todavía no exista en el sistema.

**Precondiciones:** Deben existir órdenes registradas. Para buscar vales históricos, deben existir atenciones capturadas.

**Flujo principal:**

1. El usuario accede a la consulta correspondiente.
2. Ingresa el número de vale, número de orden o entidad/institución; opcionalmente selecciona un rango de fechas.
3. El sistema ejecuta la búsqueda aplicando los permisos del usuario.
4. El sistema presenta las órdenes o vales coincidentes y permite consultar su detalle.

**Flujos alternativos y excepciones:** Si no existen coincidencias, el sistema informa que no se encontraron resultados.

**Datos de entrada:** Número de vale, número de orden, entidad/institución y rango de fechas.

**Resultados esperados:** Listado de órdenes o vales coincidentes, respetando las restricciones del rol.

**Reglas de negocio relacionadas:** RN-002, RN-010, RN-011, RN-018.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un nombre de entidad, cuando el usuario lo utiliza como búsqueda, entonces el sistema presenta las órdenes y/o vales vinculados que tiene permitido consultar.
- Dado un número de orden, cuando se realiza la búsqueda, entonces el sistema muestra la orden y sus atenciones asociadas.
- Dado un número de vale, cuando se realiza la búsqueda, entonces el sistema presenta el vale correspondiente si existe.

### RF-016: Paginar los resultados de vales

**Módulo:** MOD-003. Gestión de vales y despachos.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá presentar los resultados de las consultas de vales mediante páginas cuando exista una cantidad elevada de registros.

**Precondiciones:** Deben existir resultados de consulta que requieran paginación.

**Flujo principal:**

1. El usuario realiza una consulta de vales.
2. El sistema presenta los resultados distribuidos en páginas.
3. El usuario selecciona otra página.
4. El sistema presenta los registros de la página seleccionada.

**Flujos alternativos y excepciones:** No se especificaron el tamaño de página ni las opciones de navegación.

**Datos de entrada:** Consulta realizada y página seleccionada.

**Resultados esperados:** Resultados de vales organizados en páginas.

**Reglas de negocio relacionadas:** Ninguna identificada.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado que una consulta devuelve numerosos vales, cuando el usuario navega entre páginas, entonces el sistema muestra los registros correspondientes a la página seleccionada.

### RF-017: Corregir datos descriptivos de un vale atendido

**Módulo:** MOD-003. Atención de vales y verificación administrativa.  
**Actor principal:** Administrador.

**Descripción:**

El sistema deberá permitir que el administrador corrija datos descriptivos del vale cuando se detecte un error durante la revisión administrativa, previa confirmación. Esta operación no podrá cambiar directamente la cantidad real despachada, la identidad del grifero ni la fecha y hora de la atención, porque esos datos forman parte del registro operativo.

**Precondiciones:** El vale debe existir y el usuario debe tener permisos de corrección.

**Flujo principal:**

1. El administrador localiza el vale observado o pendiente.
2. Selecciona la corrección de datos descriptivos permitidos.
3. El sistema presenta los datos editables.
4. El usuario realiza la corrección y confirma.
5. El sistema guarda los datos corregidos sin alterar los despachos históricos.

**Flujos alternativos y excepciones:**

- Si el usuario no confirma, no se aplican cambios.
- Si la corrección afecta datos que determinan la identidad del vale o su asociación con una orden, el sistema deberá validar la unicidad y la consistencia de las relaciones.
- Una cantidad despachada incorrecta no se corrige editando el movimiento original; requiere el procedimiento de ajuste controlado que debe aprobarse (PD-006).

**Datos de entrada:** Vale seleccionado, campos descriptivos corregidos y confirmación.

**Resultados esperados:** Datos descriptivos actualizados; las atenciones y sus cantidades permanecen preservadas.

**Reglas de negocio relacionadas:** RN-015, RN-016, RN-017.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado un vale existente, cuando el administrador confirma la corrección de un dato descriptivo permitido, entonces el sistema guarda el cambio.
- Dado un despacho registrado, cuando se intenta modificar directamente su cantidad, entonces el sistema rechaza la modificación directa.
- Dada una corrección no confirmada, cuando el usuario cancela, entonces el sistema conserva los datos anteriores.

### RF-018: Impedir la eliminación de vales que tengan atenciones registradas

**Módulo:** MOD-003. Atención de vales y verificación administrativa.  
**Actor principal:** Sistema; solicitud realizada por Administrador o personal de oficina.

**Descripción:**

El sistema deberá impedir la eliminación de un vale que tenga una o más atenciones asociadas. En el flujo definido, el primer despacho crea el registro del vale y su primera atención en una misma operación; por tanto, los vales operativos siempre tendrán historial que debe conservarse. No se mostrará una acción de eliminación para vales atendidos.

**Precondiciones:** El vale debe existir.

**Flujo principal:**

1. Un usuario autorizado consulta el vale.
2. El usuario solicita eliminarlo, si la interfaz permite presentar esa acción por compatibilidad administrativa.
3. El sistema comprueba si existen atenciones.
4. Si existen atenciones, el sistema bloquea la eliminación y explica que el vale forma parte del historial de despachos.

**Flujos alternativos y excepciones:** Si no existen atenciones, la posibilidad de eliminar un borrador no aplica al flujo normal porque el vale se crea junto con su primera atención.

**Datos de entrada:** Identificador del vale.

**Resultados esperados:** El vale atendido y sus movimientos permanecen conservados.

**Reglas de negocio relacionadas:** RN-014, RN-017.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un vale con al menos una atención, cuando un usuario solicita eliminarlo, entonces el sistema bloquea la operación y conserva el vale y sus atenciones.

### RF-019: Registrar la atención de un vale presentado por el cliente

**Módulo:** MOD-003. Atención de vales y verificación administrativa.  
**Actor principal:** Grifero.

**Descripción:**

El sistema deberá permitir que el grifero registre la atención de un vale físico en el momento de realizar el despacho, sin requerir que el vale haya sido registrado previamente por Oficina. En la primera atención se capturarán los datos del vale y se creará su registro junto con el despacho. En atenciones posteriores del mismo vale, se registrará un nuevo despacho contra el saldo restante.

El sistema deberá diferenciar la cantidad autorizada indicada en el vale de la cantidad realmente despachada. Por ejemplo, si el vale autoriza 10 galones y el cliente recibe 5, el sistema registrará 10 galones autorizados, 5 galones despachados y 5 galones pendientes en ese vale.

**Precondiciones:**

- La orden de compra debe estar registrada.
- El grifero debe estar autenticado y autorizado.
- La orden debe tener saldo disponible para el tipo de combustible solicitado.

**Flujo principal:**

1. El grifero busca la orden por número o entidad/institución.
2. El sistema muestra el saldo disponible por tipo de combustible.
3. El grifero selecciona el tipo de combustible y captura el número del vale, la entidad/institución emisora y la cantidad autorizada que figura en el documento.
4. Si el vale ya existe, el sistema presenta su cantidad autorizada, el total previamente despachado y su saldo restante; el grifero no crea otro vale duplicado.
5. El grifero ingresa la cantidad realmente despachada en esta atención.
6. El sistema valida que la cantidad sea mayor que cero y no supere el saldo actual de la orden ni el saldo restante del vale. Para un vale nuevo, también verifica que el despacho no supere la cantidad autorizada indicada.
7. El sistema registra, en una sola operación, el vale cuando es su primera atención y el despacho realizado.
8. El sistema identifica automáticamente al grifero, la sede desde la que opera y la fecha y hora del servidor.
9. El sistema actualiza los saldos y estados correspondientes y presenta el resultado.

**Flujos alternativos y excepciones:**

- Si la orden no existe o no tiene saldo suficiente, el sistema no permite registrar el despacho.
- Si el vale existente no tiene saldo restante, el sistema informa que está completamente atendido y no permite otro despacho.
- Si la cantidad ingresada supera el saldo de la orden o del vale, el sistema rechaza toda la operación sin modificar ningún saldo.
- Si se interrumpe la conexión antes de recibir confirmación, la interfaz no deberá asumir que el despacho fue guardado; al recuperar conexión consultará el resultado antes de permitir un reintento para evitar duplicados.
- La captura del vale y el despacho deben confirmarse atómicamente: ambos se guardan o ninguno se guarda.

**Datos de entrada:** Orden de compra, entidad/institución, número del vale, tipo de combustible, cantidad autorizada indicada en el vale (solo en la primera atención) y cantidad realmente despachada en la atención actual. La identidad del grifero, sede y fecha/hora se obtienen del contexto autenticado y del servidor.

**Resultados esperados:** Vale creado en su primera atención o reutilizado en una atención posterior; despacho registrado; saldos actualizados; disponibilidad restante del vale visible; registro pendiente de verificación por Oficina.

**Reglas de negocio relacionadas:** RN-001, RN-002, RN-005, RN-006, RN-007, RN-008, RN-012, RN-013, RN-018, RN-020.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden con saldo suficiente y un vale nuevo de 10 galones, cuando el grifero despacha 5 galones, entonces el sistema crea el vale, registra una atención de 5 y muestra 5 galones restantes en el vale; la orden se descuenta solamente en 5 galones.
- Dado un vale con 5 galones restantes, cuando el cliente recibe 2 galones en una atención posterior, entonces el sistema registra un nuevo despacho y muestra 3 galones restantes.
- Dado que la cantidad solicitada supera el saldo de la orden o del vale, cuando el grifero intenta confirmar, entonces el sistema rechaza la operación sin alterar los saldos.
- Dado que el vale todavía no existe en el sistema, cuando el grifero lo atiende por primera vez, entonces puede capturar sus datos en el mismo flujo del despacho.

### RF-020: Calcular el saldo disponible de las órdenes de compra

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema; consulta por usuarios autorizados.

**Descripción:** El sistema deberá calcular automáticamente el saldo de cada orden y de cada tipo de combustible. El saldo se obtendrá restando de la cantidad autorizada en la orden la suma de los galones efectivamente despachados en todas las atenciones asociadas a esa orden y tipo de combustible. Los galones autorizados en vales que todavía no se han despachado no se contabilizan como consumo.

**Precondiciones:** La orden debe estar registrada con sus líneas de combustible y cantidades.

**Flujo principal:**

1. El sistema obtiene la cantidad autorizada de la línea de combustible.
2. Suma los galones reales de los despachos registrados para esa orden y combustible.
3. Calcula el saldo restante.
4. Presenta el saldo actualizado.

**Flujos alternativos y excepciones:** El saldo nunca puede ser negativo. Si una modificación administrativa de la orden pudiera dejar el saldo por debajo de los galones ya despachados, el sistema deberá rechazarla.

**Datos de entrada:** Cantidad autorizada por tipo de combustible y total de galones efectivamente despachados.

**Resultados esperados:** Saldo disponible por orden y tipo de combustible.

**Reglas de negocio relacionadas:** RN-005, RN-006, RN-008.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden de 100 galones y despachos acumulados de 35 galones del mismo combustible, cuando se consulta el saldo, entonces el sistema muestra 65 galones disponibles.

### RF-021: Calcular el saldo restante de cada vale

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema; consulta por usuarios autorizados.

**Descripción:** El sistema deberá calcular automáticamente el saldo restante de un vale restando de su cantidad autorizada la suma de todos los galones realmente despachados en sus atenciones. El vale podrá tener varias atenciones parciales hasta consumir su cantidad autorizada o hasta que la orden de compra ya no permita más despachos.

**Precondiciones:** El vale debe haberse creado durante su primera atención.

**Flujo principal:**

1. El sistema obtiene los galones autorizados del vale.
2. Suma los galones efectivamente despachados en todas sus atenciones.
3. Calcula el saldo restante.
4. Presenta la cantidad autorizada, la cantidad acumulada atendida y el saldo disponible.

**Flujos alternativos y excepciones:** El saldo no puede ser negativo. Si llega a cero, el vale queda completamente atendido.

**Datos de entrada:** Cantidad autorizada y suma de despachos efectivos del vale.

**Resultados esperados:** Saldo restante del vale actualizado.

**Reglas de negocio relacionadas:** RN-007, RN-008, RN-020.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un vale autorizado por 10 galones con despachos acumulados de 5, cuando se consulta, entonces el sistema muestra 5 galones restantes.
- Dado el mismo vale después de un despacho adicional de 5 galones, cuando se consulta, entonces el sistema muestra saldo cero y estado completamente atendido.

### RF-022: Validar los saldos antes de confirmar un despacho

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema, durante la operación del Grifero.

**Descripción:** El sistema deberá validar el saldo de la orden de compra antes de cada despacho. Cuando el vale ya exista, también deberá validar su saldo restante. En la primera atención, deberá comprobar que la cantidad realmente despachada no supere la cantidad autorizada indicada en el vale.

**Precondiciones:** La orden debe existir y el tipo de combustible solicitado debe corresponder a una línea de la orden.

**Flujo principal:**

1. El grifero selecciona la orden y el tipo de combustible.
2. Ingresa la cantidad que realmente se despachará.
3. El sistema obtiene el saldo actual de la orden y, si existe, del vale.
4. El sistema verifica que el despacho sea mayor que cero y no supere ninguno de los saldos aplicables.
5. Si las validaciones se cumplen, permite confirmar la operación.

**Flujos alternativos y excepciones:** Si la orden no tiene saldo, el vale no tiene saldo o la cantidad supera alguno de los límites, el sistema bloquea el despacho y muestra el saldo disponible.

**Datos de entrada:** Orden, tipo de combustible, vale (si ya existe), cantidad autorizada (si es nuevo) y cantidad real a despachar.

**Resultados esperados:** Solo se habilita el registro cuando la cantidad cumple todos los límites.

**Reglas de negocio relacionadas:** RN-005, RN-007, RN-020.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado que el saldo de la orden y del vale es suficiente, cuando se ingresa una cantidad válida, entonces el sistema permite confirmar.
- Dado que la cantidad supera el saldo disponible de la orden o del vale, cuando se intenta confirmar, entonces el sistema bloquea el despacho.

### RF-023: Actualizar los saldos de forma atómica después de un despacho

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema.

**Descripción:** El sistema deberá reflejar automáticamente los galones realmente despachados en los saldos del vale y de la orden de compra. El registro del despacho y la actualización de la información deberán completarse como una sola transacción: si alguna parte falla, no se guardará parcialmente ni se modificarán los saldos.

**Precondiciones:** El despacho debe haber superado las validaciones del RF-022.

**Flujo principal:**

1. El sistema registra la atención.
2. Recalcula el saldo del vale y de la línea de combustible de la orden.
3. Actualiza automáticamente los estados afectados.
4. Confirma la transacción.
5. Presenta los nuevos saldos.

**Flujos alternativos y excepciones:** Si la transacción falla, el sistema revierte todos sus cambios y mantiene los saldos previos.

**Datos de entrada:** Atención confirmada y galones realmente despachados.

**Resultados esperados:** Información consistente y saldos actualizados sin registros parciales.

**Reglas de negocio relacionadas:** RN-006, RN-007, RN-008, RN-020.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un despacho válido, cuando se confirma, entonces el vale y la orden reflejan exactamente los galones despachados.
- Dado un error durante el guardado, cuando la transacción falla, entonces no queda un despacho parcial ni se alteran los saldos.

### RF-024: Consultar órdenes y saldos antes de atender combustible

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Administrador, personal de oficina y grifero según permisos.

**Descripción:** El sistema deberá permitir consultar órdenes por número o entidad/institución y mostrar cantidades autorizadas, galones despachados y saldo disponible por tipo de combustible. Para vales con atenciones previas, deberá mostrar los galones autorizados, acumulados despachados y saldo restante.

**Precondiciones:** Deben existir órdenes o vales registrados en el sistema.

**Flujo principal:**

1. El usuario busca una orden por número o entidad.
2. El sistema muestra sus líneas de combustible y saldos.
3. Si el usuario selecciona un vale existente, el sistema muestra el detalle de sus atenciones y saldo restante.

**Flujos alternativos y excepciones:** Si no se encuentra el registro, el sistema informa que no hay resultados. Si el usuario no tiene permisos, deniega la consulta.

**Datos de entrada:** Número de orden, entidad/institución o número de vale.

**Resultados esperados:** Visualización de saldos actualizados según el rol.

**Reglas de negocio relacionadas:** RN-008, RN-010, RN-011, RN-013.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un grifero autorizado, cuando consulta una orden, entonces visualiza los saldos necesarios para decidir si puede atender al cliente.
- Dado un vale parcialmente atendido, cuando se consulta, entonces se muestran el acumulado atendido y el saldo remanente.

### RF-025: Compartir los saldos entre las sedes

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema; consulta por usuarios autorizados de ambas sedes.

**Descripción:**

El sistema deberá permitir que los griferos de las sedes San José y Santa Marta consulten los saldos de las órdenes de compra y los vales compartidos, mostrando la información actualizada después de los registros de atención.

**Precondiciones:**

- Las sedes deben utilizar el mismo conjunto de información operativa.
- Los registros y saldos deben encontrarse disponibles para consulta.

**Flujo principal:**

1. Un grifero de cualquiera de las sedes accede a la consulta de saldos.
2. El sistema obtiene la información compartida.
3. El sistema muestra el saldo disponible de la orden o del vale.
4. Después de una atención registrada, los usuarios autorizados pueden consultar el saldo actualizado.

**Flujos alternativos y excepciones:** No se definió cómo se asigna cada orden a una sede ni si determinados vales pueden atenderse exclusivamente en una sede.

**Datos de entrada:** Orden de compra o vale consultado y sede desde la que accede el usuario, si corresponde.

**Resultados esperados:** Los usuarios autorizados de ambas sedes pueden consultar los saldos compartidos y actualizados.

**Reglas de negocio relacionadas:** RN-013.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un saldo actualizado en el sistema, cuando un grifero de cualquiera de las dos sedes consulta la orden o el vale, entonces visualiza el saldo disponible registrado.

### RF-026: Actualizar automáticamente los estados de órdenes y vales según su saldo

**Módulo:** MOD-004. Control de saldos y estados.  
**Actor principal:** Sistema.

**Descripción:** El sistema deberá calcular y actualizar automáticamente el estado operativo de las órdenes y vales a partir de sus saldos. Ningún usuario cambiará manualmente estos estados.

**Estados propuestos:**

- Orden: `CON_SALDO` cuando el saldo sea mayor que cero; `AGOTADA` cuando sea cero.
- Vale: `PENDIENTE` cuando todavía no tenga galones despachados; `PARCIALMENTE_ATENDIDO` cuando tenga despachos y conserve saldo; `ATENDIDO` cuando su saldo llegue a cero. En el flujo actual, el vale se crea en su primera atención, por lo que normalmente nacerá como `PARCIALMENTE_ATENDIDO` o `ATENDIDO`.
- Verificación administrativa: `PENDIENTE_VERIFICACION` o `VERIFICADO`. Este estado es independiente del estado de consumo del vale.

**Precondiciones:** La orden o el vale debe existir y sus cantidades deben poder calcularse.

**Flujo principal:**

1. El sistema calcula el saldo tras registrar o modificar una información que afecte cantidades autorizadas.
2. Determina el estado operativo correspondiente.
3. Actualiza el estado automáticamente.
4. Presenta el estado en las consultas y reportes.

**Flujos alternativos y excepciones:** El usuario no podrá forzar manualmente estados de consumo. La verificación de Oficina no altera el saldo ni el estado operativo.

**Datos de entrada:** Saldos calculados y, para verificación, confirmación administrativa.

**Resultados esperados:** Estados consistentes con los saldos y con la revisión administrativa.

**Reglas de negocio relacionadas:** RN-009, RN-019, RN-020.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dada una orden con saldo mayor que cero, cuando se consulta, entonces figura como `CON_SALDO`; al llegar a cero cambia automáticamente a `AGOTADA`.
- Dado un vale con cantidad autorizada de 10 y despachos acumulados de 5, cuando se consulta, entonces figura como parcialmente atendido y conserva saldo de 5.
- Dado un vale cuyo saldo llega a cero, cuando se consulta, entonces figura como atendido.
- Dado un vale pendiente de revisión física, cuando Oficina lo verifica, entonces cambia únicamente su estado de verificación.

### RF-027: Generar reportes de órdenes de compra

**Módulo:** MOD-005. Reportes y panel principal.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá permitir generar reportes de las órdenes de compra, incluyendo información sobre los saldos disponibles, las cantidades de combustible y los tipos de combustible registrados.

**Precondiciones:** Deben existir órdenes de compra registradas.

**Flujo principal:**

1. El usuario autorizado accede al módulo de reportes.
2. Selecciona el reporte de órdenes de compra.
3. El sistema obtiene la información de las órdenes.
4. El sistema presenta los datos del reporte.

**Flujos alternativos y excepciones:** El detalle completo de columnas y totales del reporte está pendiente de definición.

**Datos de entrada:** Tipo de reporte y, cuando corresponda, filtros seleccionados.

**Resultados esperados:** Reporte con información de órdenes de compra, saldos y cantidades por tipo de combustible.

**Reglas de negocio relacionadas:** RN-010, RN-014.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado que existen órdenes registradas, cuando el administrador o un trabajador de oficina genera el reporte, entonces el sistema presenta las órdenes y los saldos disponibles.

### RF-028: Generar reportes de vales atendidos

**Módulo:** MOD-005. Reportes y panel principal.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá permitir generar reportes de los vales atendidos, con información consultable por horas, días, semanas y meses. El levantamiento también señala la necesidad de conocer la cantidad y el tipo de combustible atendido, así como el precio del combustible despachado por horas.

**Precondiciones:** Deben existir atenciones de vales registradas.

**Flujo principal:**

1. El usuario autorizado accede al módulo de reportes.
2. Selecciona el reporte de vales atendidos.
3. Selecciona el período de consulta.
4. El sistema obtiene los registros correspondientes.
5. El sistema presenta el reporte.

**Flujos alternativos y excepciones:** La respuesta sobre los datos exactos que debe contener cada reporte está incompleta. Deben confirmarse las columnas, los importes y la forma de agrupar las atenciones por hora.

**Datos de entrada:** Tipo de reporte y período de consulta.

**Resultados esperados:** Reporte de vales atendidos durante el período seleccionado.

**Reglas de negocio relacionadas:** RN-010, RN-012, RN-014.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado que existen vales atendidos, cuando el usuario genera el reporte para un período seleccionado, entonces el sistema presenta las atenciones registradas en ese período.

### RF-029: Filtrar reportes

**Módulo:** MOD-005. Reportes y panel principal.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá permitir filtrar los reportes por fechas, usuarios y estados de las órdenes de compra y de los vales, incluyendo la identificación de registros que tienen saldo y registros que no tienen saldo.

**Precondiciones:** Deben existir datos que puedan utilizarse en los filtros.

**Flujo principal:**

1. El usuario selecciona el tipo de reporte.
2. El sistema presenta los filtros disponibles.
3. El usuario selecciona fechas, usuarios o estados.
4. El sistema aplica los filtros.
5. El sistema presenta los resultados que cumplen los criterios.

**Flujos alternativos y excepciones:** Si no existen resultados para los filtros seleccionados, el sistema informa que no hay datos para mostrar.

**Datos de entrada:** Rango de fechas, usuario y estado.

**Resultados esperados:** Reporte filtrado según los criterios indicados.

**Reglas de negocio relacionadas:** RN-009, RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un reporte con registros de distintos períodos y usuarios, cuando el usuario aplica filtros de fecha y usuario, entonces el sistema presenta únicamente los registros que cumplen ambos criterios.
- Dado un filtro por estado, cuando el usuario solicita los registros con saldo o sin saldo, entonces el sistema muestra los registros del estado seleccionado.

### RF-030: Visualizar un panel principal con gráficos interactivos

**Módulo:** MOD-005. Reportes y panel principal.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá presentar un panel principal con reportes y gráficos interactivos al ingresar al sistema, utilizando los filtros identificados para consultar la información de órdenes de compra y vales.

**Precondiciones:**

- El usuario debe tener el rol Administrador u Oficina.
- Debe existir información para presentar.

**Flujo principal:**

1. El administrador o trabajador de oficina accede al sistema.
2. El sistema presenta el panel principal.
3. El sistema muestra los reportes y gráficos disponibles.
4. El usuario aplica los filtros permitidos.
5. El sistema actualiza la información presentada según los filtros.

**Flujos alternativos y excepciones:** Si no existen datos para el período o los filtros seleccionados, el sistema deberá mostrar que no hay información disponible. No se solicitaron indicadores de rendimiento ni análisis estadísticos avanzados.

**Datos de entrada:** Filtros de fechas, usuarios y estados.

**Resultados esperados:** Panel con reportes y gráficos interactivos relacionados con órdenes de compra, saldos y vales atendidos.

**Reglas de negocio relacionadas:** RN-010, RN-014.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un usuario Administrador u Oficina, cuando ingresa al sistema, entonces visualiza el panel principal con los reportes y gráficos disponibles.
- Dado que el usuario modifica los filtros, cuando aplica los nuevos criterios, entonces los gráficos y reportes se actualizan de acuerdo con ellos.

### RF-031: Exportar reportes a PDF y Excel

**Módulo:** MOD-005. Reportes y panel principal.  
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá permitir exportar los reportes disponibles en formatos PDF y Excel.

**Precondiciones:** El usuario debe tener permiso para consultar el reporte.

**Flujo principal:**

1. El usuario genera o consulta un reporte.
2. Selecciona el formato PDF o Excel.
3. El sistema prepara el archivo correspondiente.
4. El sistema permite obtener el archivo exportado.

**Flujos alternativos y excepciones:** El contenido exacto de los gráficos en cada formato debe confirmarse.

**Datos de entrada:** Reporte consultado y formato de exportación.

**Resultados esperados:** Archivo del reporte en formato PDF o Excel.

**Reglas de negocio relacionadas:** RN-010.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un reporte disponible, cuando el usuario selecciona PDF, entonces el sistema genera un archivo en ese formato.
- Dado un reporte disponible, cuando el usuario selecciona Excel, entonces el sistema genera un archivo en ese formato.

### RF-032: Ordenar las órdenes de compra

**Módulo:** MOD-002. Gestión de órdenes de compra.    
**Actor principal:** Administrador y personal de oficina.

**Descripción:**

El sistema deberá permitir ordenar los registros de órdenes de compra durante su consulta, además de aplicar los filtros disponibles.

**Precondiciones:** Deben existir órdenes de compra registradas.

**Flujo principal:**

1. El usuario accede al listado de órdenes de compra.
2. Selecciona el criterio de ordenación disponible.
3. El sistema organiza los resultados según el criterio seleccionado.
4. El sistema presenta el listado ordenado.

**Flujos alternativos y excepciones:** Los criterios concretos de ordenación, como fecha o número, y el sentido ascendente o descendente están pendientes de confirmación.

**Datos de entrada:** Criterio y sentido de ordenación.

**Resultados esperados:** Listado de órdenes de compra ordenado según los criterios seleccionados.

**Reglas de negocio relacionadas:** Ninguna identificada.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado un listado de órdenes de compra, cuando el usuario selecciona un criterio de ordenación, entonces el sistema presenta los registros ordenados de acuerdo con ese criterio.

### RF-033: Ordenar los vales

**Módulo:** MOD-003. Gestión de vales y despachos.    
**Actor principal:** Administrador y personal de oficina; otros usuarios únicamente en los listados permitidos por su rol.

**Descripción:**

El sistema deberá permitir ordenar los registros de vales durante su consulta, además de aplicar los filtros disponibles.

**Precondiciones:** Deben existir vales registrados.

**Flujo principal:**

1. El usuario accede al listado de vales.
2. Selecciona el criterio de ordenación disponible.
3. El sistema organiza los resultados según el criterio seleccionado.
4. El sistema presenta el listado ordenado.

**Flujos alternativos y excepciones:** Los criterios concretos de ordenación y el sentido ascendente o descendente están pendientes de confirmación.

**Datos de entrada:** Criterio y sentido de ordenación.

**Resultados esperados:** Listado de vales ordenado según los criterios seleccionados.

**Reglas de negocio relacionadas:** RN-010, RN-011.

**Prioridad:** Media.

**Criterios de aceptación:**

- Dado un listado de vales, cuando el usuario selecciona un criterio de ordenación, entonces el sistema presenta los registros ordenados de acuerdo con ese criterio.

## 4.7. OCR para órdenes de compra

### RF-034: Procesar PDF de órdenes de compra mediante RapidOCR

**Módulo:** MOD-006. OCR para órdenes de compra.  
**Actor principal:** Personal de oficina y Administrador, según permisos de gestión de órdenes.

**Descripción:** El sistema deberá permitir cargar exclusivamente archivos PDF de órdenes de compra para extraer mediante OCR los campos necesarios y autocompletar el formulario de registro. Se utilizará RapidOCR como decisión tecnológica del proyecto. El OCR es una ayuda de captura: el usuario debe revisar y confirmar todos los datos antes de registrar la orden.

**Precondiciones:** El usuario debe estar autorizado para registrar órdenes y disponer de un PDF de una orden de compra.

**Flujo principal:**

1. El usuario abre el formulario de una nueva orden.
2. Carga el archivo PDF.
3. El sistema procesa las páginas con RapidOCR.
4. El sistema identifica y extrae, cuando sea posible, número de orden, expediente SIAF, fecha, proveedor, unidad ejecutora, RUC, tipo de combustible, cantidad, precio unitario y precio total.
5. El sistema autocompleta los campos reconocidos y deja señalados los campos no reconocidos.
6. El usuario revisa, corrige y completa los datos.
7. El sistema valida los campos obligatorios y guarda la orden solamente después de la confirmación del usuario.
8. El sistema descarta el archivo temporal una vez terminado el procesamiento, salvo que una política de conservación sea aprobada posteriormente.

**Flujos alternativos y excepciones:**

- Si el PDF está dañado, protegido, vacío o no puede leerse, el sistema informa el problema y permite ingresar los datos manualmente.
- Si el OCR no reconoce un campo, este queda vacío para su completado manual.
- Un texto reconocido no se considera dato confirmado hasta que el usuario lo revise.
- El OCR no se utiliza para registrar vales ni para reconocer fotografías u otros formatos en esta versión.

**Datos de entrada:** Archivo PDF de una orden de compra.

**Resultados esperados:** Formulario de orden de compra autocompletado parcialmente o totalmente con los datos extraídos y listo para revisión; la orden solo se persiste después de la confirmación.

**Reglas de negocio relacionadas:** RN-003, RN-021.

**Prioridad:** Alta.

**Criterios de aceptación:**

- Dado un PDF válido y legible, cuando el usuario lo procesa, entonces el sistema extrae los campos reconocibles y autocompleta el formulario.
- Dado un campo que OCR no reconoce, cuando termina el procesamiento, entonces queda disponible para completar manualmente.
- Dado que el usuario no ha revisado y confirmado el formulario, cuando termina el OCR, entonces la orden no se guarda.
- Dado un archivo que no es PDF o no puede procesarse, cuando se carga, entonces el sistema informa el error y no crea una orden.

## 5. Reglas de negocio

| **ID** | **Regla de negocio** | **Descripción** | **Módulo relacionado** |
|---|---|---|---|
| RN-001 | Orden existente antes del despacho | Para atender un vale debe existir previamente la orden de compra a la que se imputará el consumo. El vale, en cambio, no requiere pre-registro. | MOD-002, MOD-003 |
| RN-002 | Vale creado en la primera atención | El registro del vale se crea en el mismo proceso en que el grifero registra su primer despacho. Oficina no crea un segundo registro. | MOD-003 |
| RN-003 | Datos obligatorios de la orden | La orden debe contener número, expediente SIAF, fecha, proveedor, unidad ejecutora, RUC de la unidad ejecutora y una o más líneas de combustible con tipo, cantidad, precio unitario y precio total. | MOD-002 |
| RN-004 | Datos obligatorios del vale | En la primera atención se debe capturar número del vale, entidad/institución emisora, orden relacionada, tipo de combustible y cantidad autorizada indicada en el documento. | MOD-003 |
| RN-005 | Límite de despacho por orden | La cantidad realmente despachada no puede superar el saldo disponible de la orden para el tipo de combustible correspondiente. | MOD-003, MOD-004 |
| RN-006 | Descuento de la orden por consumo real | El saldo de la orden disminuye únicamente por los galones efectivamente despachados, no por el total autorizado escrito en un vale. | MOD-004 |
| RN-007 | Saldo remanente del vale | El saldo del vale equivale a la cantidad autorizada menos la suma de los galones efectivamente despachados en sus atenciones. | MOD-003, MOD-004 |
| RN-008 | Cálculo automático | Los saldos se calculan automáticamente después de cada atención confirmada. No se editan manualmente. | MOD-004 |
| RN-009 | Estados automáticos | Los estados de consumo de órdenes y vales cambian automáticamente según el saldo. Los usuarios no los cambian manualmente. | MOD-004 |
| RN-010 | Permisos predefinidos por rol | El Administrador accede a todos los módulos; Oficina gestiona órdenes, verifica vales y consulta reportes; Grifero consulta órdenes/saldos y registra sus despachos. El sistema muestra solo módulos permitidos y el backend valida cada operación. | MOD-001 y todos los módulos |
| RN-011 | Restricción operativa del grifero | El grifero no registra órdenes ni verifica vales. Solo consulta la información necesaria y captura las atenciones que realiza. | MOD-001, MOD-003, MOD-004 |
| RN-012 | Identificación del despacho | Cada despacho registra automáticamente al grifero autenticado, la fecha y hora del servidor y la sede desde la que se realizó. | MOD-003 |
| RN-013 | Saldos compartidos entre sedes | Los usuarios autorizados de San José y Santa Marta consultan la misma información centralizada y actualizada. | MOD-004 |
| RN-014 | Conservación de registros históricos | Los despachos y vales atendidos no se eliminan, para preservar el historial y la correcta atribución de las operaciones. Los usuarios que dejan de trabajar se deshabilitan, no se eliminan. | MOD-001, MOD-003 |
| RN-015 | Confirmación de operaciones administrativas | Las modificaciones y eliminaciones permitidas requieren confirmación del usuario. La confirmación no reemplaza las validaciones de negocio. | MOD-001, MOD-002, MOD-003 |
| RN-016 | Eliminación condicionada de órdenes | Una orden solo puede eliminarse si no tiene vales ni atenciones asociados. Si tiene al menos un vale asociado, la operación se bloquea y se muestra una alerta. | MOD-002 |
| RN-017 | Protección de atenciones confirmadas | Un despacho confirmado no se edita ni elimina directamente. Los errores de cantidad deben corregirse mediante un procedimiento de ajuste trazable que queda pendiente de aprobación del negocio. | MOD-003, MOD-004 |
| RN-018 | Identificación de vales | Para evitar colisiones de numeración, la identificación funcional del vale considera como mínimo la entidad emisora, el número del vale y la orden asociada. El sistema debe advertir duplicados antes de crear otro vale. | MOD-003 |
| RN-019 | Verificación posterior por Oficina | Oficina verifica los datos capturados por el grifero contra el vale físico recibido. Verificar no crea otro registro ni modifica cantidades despachadas. | MOD-003 |
| RN-020 | Atenciones parciales | Un vale puede atenderse en varios despachos. Cada despacho descuenta únicamente su cantidad real y el vale conserva el saldo no atendido hasta agotarse o hasta que la orden deje de tener saldo. | MOD-003, MOD-004 |
| RN-021 | OCR asistido y revisado | RapidOCR procesa únicamente PDFs de órdenes de compra. El resultado sirve para prellenar el formulario y debe ser revisado y confirmado por Oficina antes de guardar la orden. | MOD-002, MOD-006 |
| RN-022 | Integridad de órdenes con despachos | Una modificación de cantidades o líneas de combustible no puede reducir el total autorizado por debajo de los galones ya despachados ni alterar la relación histórica de los despachos. | MOD-002, MOD-004 |

---

## 6. Matriz de permisos por actor

Los permisos se asignan mediante tres perfiles predefinidos. El Administrador puede acceder a todos los módulos. Oficina y Grifero solo visualizan los módulos y acciones correspondientes a su rol. La interfaz oculta las opciones no autorizadas y el backend aplica la validación definitiva. No se contempla personalizar permisos individuales fuera de los perfiles en esta versión.

| **Módulo / Funcionalidad** | **Administrador** | **Oficina** | **Grifero** |
|---|---|---|---|
| Administración de usuarios | Permitido | No permitido | No permitido |
| Asignar rol y habilitar/deshabilitar usuarios | Permitido | No permitido | No permitido |
| Gestión de órdenes: registrar, consultar y modificar | Permitido | Permitido | No permitido |
| Eliminar orden sin vales asociados | Permitido | Permitido | No permitido |
| Consultar órdenes y saldos necesarios para despacho | Permitido | Permitido | Permitido |
| Capturar vale en la primera atención y registrar despacho | Permitido | No permitido | Permitido, solo sus atenciones |
| Consultar vales y saldos | Permitido | Permitido | Permitido, para atender combustible |
| Verificar vales físicos recibidos | Permitido | Permitido | No permitido |
| Corregir datos descriptivos de vales | Permitido | No permitido | No permitido |
| Eliminar vales con atenciones | No permitido | No permitido | No permitido |
| Consultar todas las atenciones de griferos | Permitido | Según el alcance de consulta administrativa | Solo sus propias atenciones |
| Reportes, dashboard y gráficos | Permitido | Permitido | No permitido |
| Exportar reportes a PDF y Excel | Permitido | Permitido | No permitido |
| Procesar PDF de orden mediante OCR | Permitido | Permitido | No permitido |

**Reglas de aplicación:**

- Al iniciar sesión, el menú se construye a partir de los permisos asociados al rol devuelto por el backend.
- Las rutas protegidas y botones se ocultan o deshabilitan según el permiso.
- El backend debe rechazar cualquier operación no autorizada aunque el usuario intente invocarla directamente.
- Los griferos no pueden consultar precios unitarios, precios totales ni otros datos administrativos que no sean necesarios para el despacho; el detalle exacto de información confidencial se mantiene sujeto a la definición PD-013.

---

## 7. Matriz de trazabilidad

Los identificadores P-001 a P-019 representan las secciones temáticas del levantamiento. Se actualizan las relaciones para reflejar el nuevo flujo: el grifero captura el vale al despacharlo y Oficina lo verifica posteriormente.

| **ID de pregunta** | **Tema del levantamiento** | **RF relacionado** | **Módulo** |
|---|---|---|---|
| P-001 | Información general, actividad, trabajadores y sedes | RF-025 | MOD-004 |
| P-002 | Problemas de registro manual, errores y saldos | RF-014, RF-019 a RF-024 | MOD-003 y MOD-004 |
| P-003 | Objetivos, expectativas y funcionalidades indispensables | RF-007, RF-014, RF-019 a RF-024, RF-027 a RF-031 | MOD-002 a MOD-005 |
| P-004 | Usuarios, roles y responsabilidades | RF-001 a RF-006 | MOD-001 |
| P-005 | Proceso de orden, presentación de vale, despacho y revisión en oficina | RF-007, RF-013, RF-014, RF-019 | MOD-002 y MOD-003 |
| P-006 | Información y datos manejados | RF-007, RF-019 a RF-021, RF-034 | MOD-002 a MOD-004 y MOD-006 |
| P-007 | Consulta, búsqueda, modificación, eliminación, paginación y ordenación | RF-008 a RF-018, RF-032, RF-033 | MOD-002 y MOD-003 |
| P-008 | Operaciones, cantidades, transacciones y saldos | RF-019 a RF-024 | MOD-003 y MOD-004 |
| P-009 | Estados y seguimiento de atenciones | RF-013, RF-019, RF-026 | MOD-003 y MOD-004 |
| P-010 | Reportes, filtros, gráficos y consultas | RF-006, RF-027 a RF-031 | MOD-001 y MOD-005 |
| P-011 | Documentos de órdenes de compra y OCR | RF-007, RF-034 | MOD-002 y MOD-006 |
| P-012 | Notificaciones y alertas | Sin RF: no se requieren notificaciones. La alerta de bloqueo de eliminación es un mensaje de validación dentro de la pantalla. | No aplica |
| P-013 | Administración de usuarios y permisos | RF-001 a RF-005 | MOD-001 |
| P-014 | Integraciones externas | Sin RF: no se requieren integraciones externas. | No aplica |
| P-015 | Situaciones excepcionales | RF-004, RF-012, RF-017 a RF-019, RF-022, RF-034 | MOD-001 a MOD-004 y MOD-006 |
| P-016 | Migración e históricos | Sin RF de migración. Los registros creados en el sistema sí se consultan históricamente. | MOD-002, MOD-003, MOD-005 |
| P-017 | Acceso desde PC, móviles y sedes | RF-002, RF-003, RF-005, RF-014, RF-024, RF-025 | MOD-001 y MOD-004 |
| P-018 | Seguridad y trazabilidad | RF-002 a RF-006, RF-019 | MOD-001 y MOD-003 |
| P-019 | Priorización | RF-007, RF-013, RF-019 a RF-024, RF-027 a RF-031, RF-034 | MOD-002 a MOD-006 |

---

## 8. Matriz de cobertura funcional

| **Módulo** | **Funcionalidad identificada** | **RF relacionado** | **Estado** |
|---|---|---|---|
| MOD-001 | Registro de usuarios | RF-001 | Documentado |
| MOD-001 | Asignación de roles y restricción de módulos/acciones | RF-002 | Documentado |
| MOD-001 | Inicio de sesión | RF-003 | Documentado |
| MOD-001 | Habilitación y deshabilitación de cuentas sin borrar históricos | RF-004 | Documentado |
| MOD-001 | Cierre de sesión | RF-005 | Documentado |
| MOD-001 | Consulta administrativa de atenciones de griferos | RF-006 | Documentado |
| MOD-002 | Registro de órdenes con captura manual u OCR | RF-007 | Documentado |
| MOD-002 | Consulta del detalle de órdenes | RF-008 | Documentado |
| MOD-002 | Búsqueda por número y fecha | RF-009 | Documentado |
| MOD-002 | Paginación de órdenes | RF-010 | Documentado |
| MOD-002 | Modificación de órdenes | RF-011 | Documentado |
| MOD-002 | Eliminación solo cuando no existen vales asociados | RF-012 | Documentado |
| MOD-003 | Verificación de vales atendidos por Oficina | RF-013 | Documentado |
| MOD-003 | Consulta de orden y vale para atención sin pre-registro | RF-014 | Documentado |
| MOD-003 | Búsqueda por número de vale, orden o entidad | RF-015 | Documentado |
| MOD-003 | Paginación de vales/atenciones | RF-016 | Documentado |
| MOD-003 | Corrección de datos descriptivos del vale | RF-017 | Documentado |
| MOD-003 | Bloqueo de eliminación de vales atendidos | RF-018 | Documentado |
| MOD-003 | Captura del vale al primer despacho y atención parcial | RF-019 | Documentado |
| MOD-004 | Cálculo del saldo de la orden por combustible | RF-020 | Documentado |
| MOD-004 | Cálculo del saldo restante del vale | RF-021 | Documentado |
| MOD-004 | Validación previa de saldos | RF-022 | Documentado |
| MOD-004 | Actualización atómica de saldos | RF-023 | Documentado |
| MOD-004 | Consulta de saldos | RF-024 | Documentado |
| MOD-004 | Saldos compartidos entre sedes | RF-025 | Documentado |
| MOD-004 | Actualización automática de estados | RF-026 | Documentado |
| MOD-005 | Reportes de órdenes de compra | RF-027 | Documentado |
| MOD-005 | Reportes de vales/despachos por horas, días, semanas y meses | RF-028 | Documentado |
| MOD-005 | Filtros por fecha, usuario y estado | RF-029 | Documentado |
| MOD-005 | Dashboard con gráficos interactivos | RF-030 | Documentado |
| MOD-005 | Exportación de reportes a PDF y Excel | RF-031 | Documentado |
| MOD-002 | Ordenación de órdenes de compra | RF-032 | Documentado |
| MOD-003 | Ordenación de vales | RF-033 | Documentado |
| MOD-006 | Procesamiento OCR de PDF de órdenes con RapidOCR | RF-034 | Documentado |

---

## 9. Información pendiente de definición

Las siguientes decisiones no impiden documentar el flujo principal, pero deben confirmarse para cerrar el contrato funcional y técnico. Las decisiones recomendadas se presentan como propuestas y no como hechos ya aprobados.

| **ID** | **Tema** | **Información pendiente** | **Decisión recomendada / pregunta de confirmación** |
|---|---|---|---|
| PD-001 | Identificación única de órdenes | Las instituciones pueden repetir números de orden. | Propuesta: identificar una orden por entidad emisora + número de orden, y validar unicidad con ese conjunto. ¿Es suficiente para distinguir todas las órdenes? |
| PD-002 | Identificación del emisor del vale | Las instituciones y la estación pueden tener numeraciones propias. | Propuesta: guardar el emisor del vale (institución o estación) y usar emisor + número + orden como clave de búsqueda/duplicidad. Confirmar si existe otro emisor. |
| PD-003 | Reutilización del mismo vale | El ejemplo confirma atención parcial, pero no precisa si el cliente puede regresar varias veces con el mismo documento. | Propuesta: permitir múltiples despachos del mismo vale hasta consumir su saldo, registrando cada atención por separado. Confirmar que el vale físico puede reutilizarse. |
| PD-004 | Tipo de combustible en el vale | Las órdenes pueden contener más de un tipo de combustible; debe definirse cómo se identifica el combustible autorizado en cada vale. | Propuesta: exigir que cada vale/atención indique un tipo de combustible existente en la orden y calcular saldos por tipo. |
| PD-005 | Asignación de órdenes a sedes | Se comparten saldos entre sedes, pero no se definió si la orden pertenece a una sede. | Propuesta: mantener órdenes y saldos compartidos, y registrar la sede real de cada despacho. Confirmar si existen órdenes exclusivas de una sede. |
| PD-006 | Corrección de un despacho incorrecto | No se definió cómo corregir una cantidad realmente despachada que ya fue confirmada. | Propuesta: no editar ni borrar el despacho original; permitir al Administrador registrar un ajuste compensatorio con motivo, referencia y trazabilidad. Requiere aprobación del negocio. |
| PD-007 | Contraseñas | No se confirmó si los usuarios podrán cambiar o recuperar contraseñas. | ¿El usuario podrá cambiar su contraseña? ¿El administrador podrá restablecerla? ¿Se requiere recuperación por correo? |
| PD-008 | Cierre remoto de sesiones | Se confirmó cierre de sesión, pero no si el Administrador puede cerrar sesiones ajenas. | Propuesta: cada usuario cierra su propia sesión; la deshabilitación de una cuenta revoca sus sesiones. Confirmar si se necesita cierre remoto administrativo. |
| PD-009 | Contenido detallado de reportes | Se mencionan saldos, cantidades, tipo de combustible y precio de combustible atendido por hora, pero no el diseño exacto. | Confirmar columnas, agrupaciones, totales y definición de “precio atendido por hora” (precio unitario, importe despachado u otro cálculo). |
| PD-010 | Gráficos del dashboard | Se requieren gráficos interactivos, pero no se indicaron tipos ni indicadores exactos. | Propuesta inicial: gráficos de galones despachados por tipo de combustible y por hora/día/semana/mes, más resumen de saldos. Validar con el negocio. |
| PD-011 | Revisión de vale observado | Si los datos capturados por el grifero no coinciden con el vale físico, no se definió el procedimiento posterior. | Propuesta: dejarlo pendiente/observado y solicitar revisión del Administrador; no alterar el despacho ni los saldos durante la verificación. Definir quién resuelve la discrepancia. |
| PD-012 | PDF OCR | No se especificaron tamaño máximo, cantidad de páginas, PDFs protegidos ni calidad mínima. | Propuesta: admitir PDF, aplicar límites configurables y permitir registro manual cuando RapidOCR no pueda reconocer el documento. Confirmar límites operativos. |
| PD-013 | Datos confidenciales | Se indicó que Administrador y Oficina pueden consultar información confidencial; no se enumeraron todos los campos. | Propuesta: grifero ve solo datos operativos necesarios para despachar; precios y datos administrativos quedan restringidos a Administrador/Oficina. Confirmar campos exactos. |
| PD-014 | Sede en el perfil del usuario | No se estableció si un grifero pertenece a una sede o puede trabajar en ambas. | Propuesta: asociar el usuario a una sede habitual y guardar la sede real de cada despacho, permitiendo cambiarla solo según autorización. Confirmar movilidad entre sedes. |
| PD-015 | Cantidad de usuarios | Se mencionan seis trabajadores y ocho cuentas. | Confirmar si el número previsto de cuentas será ocho o si el dato de seis trabajadores sigue vigente. |
| PD-016 | Históricos anteriores al sistema | Se indicó que no se migrarán datos antiguos, pero sí se conservarán archivos históricos. | Propuesta: mantener los Excel/PDF anteriores fuera del sistema y consultar dentro del sistema solo los registros generados desde su puesta en marcha. Confirmar si esto satisface la necesidad. |
| PD-017 | Consulta fuera del horario laboral | La pregunta quedó sin respuesta. | ¿Los usuarios podrán consultar órdenes, vales y saldos fuera del horario laboral? |
| PD-018 | Ordenamiento | Se solicitó ordenar, pero no se especificaron campos. | Propuesta: permitir ordenar por fecha, número y entidad, ascendente o descendente, en los listados correspondientes. Confirmar si se requieren otros criterios. |
| PD-019 | Zona horaria de registros y reportes | No se indicó la zona horaria que debe utilizar el sistema para agrupar atenciones por hora/día. | Propuesta: almacenar fecha/hora en UTC y mostrar/agrupar usando la zona horaria de la operación en Perú (America/Lima). Confirmar. |
| PD-020 | Cantidades e importes por línea de combustible | Se describieron cantidad, descripción, precio unitario y total por tipo, pero no reglas de redondeo. | Propuesta: guardar cantidades e importes con precisión decimal y validar coherencia de total = cantidad × precio unitario, con tolerancia de redondeo definida. Confirmar decimales requeridos. |

---

## 10. Consideraciones y límites funcionales

### 10.1. Decisiones funcionales confirmadas por las nuevas indicaciones

- La orden de compra debe estar registrada antes de atender combustible.
- El vale no se registra anticipadamente por Oficina. Se captura en el sistema en el momento de su primera atención por el grifero.
- Antes de despachar, el grifero consulta el saldo disponible de la orden de compra.
- El vale puede atenderse parcialmente. Se registra la cantidad autorizada del documento y, por separado, la cantidad realmente despachada.
- Si un vale autoriza 10 galones y se despachan 5, el saldo del vale queda en 5 galones.
- Los despachos posteriores del mismo vale se registran como atenciones adicionales contra su saldo restante.
- El saldo de la orden disminuye solo por los galones realmente despachados.
- Oficina verifica después que los datos capturados por el grifero coincidan con el vale físico recibido; no vuelve a registrar la información.
- Los estados de consumo de órdenes y vales cambian automáticamente según sus saldos.
- Los permisos son predefinidos por rol. El menú muestra solo módulos y acciones autorizados, y el backend valida cada petición.
- Las cuentas de usuarios se deshabilitan en lugar de eliminarse, para preservar la autoría de los registros históricos.
- Una orden solo puede eliminarse cuando no tiene vales asociados; si tiene alguno, la operación se bloquea y se presenta una alerta.
- Los vales con atenciones registradas no pueden eliminarse.
- El OCR procesa archivos PDF de órdenes de compra y prellena el formulario; la revisión humana es obligatoria antes de guardar.

### 10.2. Reglas operativas y técnicas recomendadas

- El registro del vale en su primera atención y el registro del primer despacho deben guardarse como una sola operación indivisible.
- Cada atención debe almacenar galones reales, fecha/hora, usuario y sede.
- Los saldos deben derivarse de las cantidades autorizadas menos los despachos efectivos, agrupados por tipo de combustible.
- El frontend no calcula ni modifica saldos como fuente oficial; los consulta al backend.
- No debe permitirse editar o borrar directamente una atención confirmada. Cualquier ajuste de una atención errónea debe conservar el movimiento original y requiere aprobar el procedimiento propuesto en PD-006.
- La verificación administrativa de un vale no modifica el saldo ni reemplaza el registro de despacho.

### 10.3. Exclusiones confirmadas

- Autorregistro o registro público de usuarios.
- Acceso de clientes, proveedores u otros usuarios externos.
- Notificaciones y alertas proactivas (la alerta de bloqueo de eliminación es una validación en pantalla).
- Integración con facturación, pagos, correo, WhatsApp, mapas o sistemas gubernamentales.
- Importación o migración inicial de datos desde Excel/PDF.
- OCR de vales, fotografías u otros documentos distintos de PDFs de órdenes de compra.
- Generación automática de comprobantes, envío de documentos y almacenamiento permanente de PDFs OCR.
- Comparación de reportes entre períodos.
- Impresión directa de reportes.
- Reportes personalizados e indicadores de rendimiento.

### 10.4. Aspectos que pertenecen a otros documentos

El uso desde PC y móviles y el acceso desde ambas sedes deben desarrollarse en los requerimientos no funcionales en cuanto a compatibilidad, diseño adaptable, disponibilidad, seguridad, rendimiento y conectividad. El comportamiento ante interrupciones de red deberá especificarse también como requisito no funcional: no se ofrecerá operación offline; la interfaz deberá confirmar el resultado desde el servidor antes de permitir reintentos.

---

## 11. Resumen de requerimientos

| **Elemento** | **Cantidad** |
|---|---:|
| Actores identificados | 3 |
| Módulos identificados | 6 |
| Requerimientos funcionales vigentes | 34 |
| Reglas de negocio | 22 |
| Aspectos pendientes de confirmación | 20 |

### 11.1. Requerimientos por módulo

| **Módulo** | **Rango de RF** | **Cantidad** |
|---|---|---:|
| MOD-001. Administración de usuarios y acceso | RF-001 a RF-006 | 6 |
| MOD-002. Gestión de órdenes de compra | RF-007 a RF-012 y RF-032 | 7 |
| MOD-003. Atención de vales y verificación administrativa | RF-013 a RF-019 y RF-033 | 8 |
| MOD-004. Control de saldos y estados | RF-020 a RF-026 | 7 |
| MOD-005. Reportes y panel principal | RF-027 a RF-031 | 5 |
| MOD-006. OCR para órdenes de compra | RF-034 | 1 |
| **Total** | **RF-001 a RF-034** | **34** |

### 11.2. Cambios principales respecto a la versión anterior

- Se reemplazó la eliminación física de usuarios por habilitación/deshabilitación de cuentas.
- Se definió que los permisos vienen preconfigurados por rol y que la interfaz muestra únicamente los módulos autorizados.
- Se incorporó el OCR de PDFs de órdenes de compra como asistencia para autocompletar el formulario; el usuario revisa y confirma antes de guardar.
- Se estableció que Oficina verifica los vales atendidos y no los registra nuevamente.
- Se definió que el vale nace durante su primera atención por el grifero, sin registro previo.
- Se incorporó la atención parcial de vales y el ejemplo de 10 galones autorizados, 5 despachados y 5 restantes.
- Se limitó la eliminación de órdenes a aquellas que no tengan vales asociados.
- Se estableció que los estados cambian automáticamente según los saldos.
- Se retiraron la comparación de reportes entre períodos y la impresión directa de reportes.
- Se reorganizó la numeración para mantener los RF consecutivos del RF-001 al RF-034.

### 11.3. Prioridades

La prioridad alta corresponde al registro asistido de órdenes, la consulta previa de saldos, la captura de vales al momento del despacho, la atención parcial, la verificación de Oficina, el cálculo automático de saldos y los reportes requeridos. La operación OCR forma parte del registro de órdenes y debe estar disponible junto con el formulario, aunque el registro manual seguirá disponible como alternativa cuando el PDF no pueda procesarse.

---

## 12. Revisión de calidad del documento

### 12.1. Consistencia

- El flujo de negocio está unificado: orden registrada → cliente presenta vale → grifero consulta saldo → grifero registra vale y despacho real → Oficina verifica el documento físico.
- El vale no se pre-registra en Oficina. Su primera captura y su primer despacho se guardan de manera conjunta.
- Se distingue cantidad autorizada del vale de cantidad realmente despachada.
- El despacho parcial deja un saldo remanente reutilizable en el mismo vale.
- La orden se descuenta por consumo efectivo, no por la cantidad total autorizada del vale.
- Los estados de consumo son automáticos; la verificación administrativa se maneja como estado separado.
- Los usuarios se deshabilitan para preservar la historia; las órdenes con vales y los vales atendidos no se eliminan.
- Se retiraron las funcionalidades de comparación de reportes entre períodos e impresión directa; los identificadores se reorganizaron para conservar una secuencia consecutiva sin dejar referencias huérfanas.

### 12.2. Completitud

- Los 34 requerimientos incluyen las funcionalidades vigentes.
- El OCR se limita a PDFs de órdenes y requiere revisión humana.
- Se incorporó el control de duplicidad de vales y la captura de usuario, fecha/hora y sede para cada despacho.
- Las decisiones que aún requieren confirmación están registradas en la sección 9.

### 12.3. Trazabilidad

- Cada RF está relacionado con las secciones temáticas del levantamiento.
- Las reglas de negocio se relacionan con los RF correspondientes.
- Las matrices de permisos y cobertura reflejan los cambios del flujo operativo.

### 12.4. Verificabilidad

- Los criterios de aceptación incluyen escenarios de primera atención, atenciones parciales, agotamiento de saldo, verificación administrativa, eliminación bloqueada y OCR con revisión humana.
- La integridad de los saldos se verifica por tipo de combustible y por cantidades realmente despachadas.

### 12.5. Identificación

- Los actores utilizan identificadores ACT consecutivos.
- Los módulos utilizan identificadores MOD consecutivos.
- Los requerimientos funcionales utilizan identificadores RF consecutivos y únicos, del RF-001 al RF-034.
- Las reglas de negocio utilizan identificadores RN consecutivos y únicos, del RN-001 al RN-022.
- Los puntos pendientes utilizan identificadores PD consecutivos y únicos, del PD-001 al PD-020.

---

**Fin del documento.**

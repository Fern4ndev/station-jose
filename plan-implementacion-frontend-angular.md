# Plan de implementación del frontend (Angular 21.2.0)

**Proyecto:** Sistema web con OCR para la gestión de combustible institucional, estación de servicio San José, Abancay
**Documento complementario de:** `plan-implementacion-backend-fastapi.md` y `requerimientos-funcionales-sistema.md` (v3.0)
**Versión del plan:** 3.2 (reemplaza a `plan-implementacion-frontend.md`, basado en Livewire; la 3.1 acompañó el cambio del backend a PostgreSQL 16 con pgAdmin 4; la 3.2 fija el proyecto Angular en la **raíz del repositorio**, sin carpeta `frontend/`, y autoriza PrimeNG, `iconify-icon`, Tailwind y `chart.js`)
**Fecha de corte del estado:** 30 de octubre de 2026

**Cómo usar este archivo:** cada tarea es una casilla. Al terminarla, cambia `- [ ]` por `- [x]`. Un bloque se cierra solo cuando pasa su **Verificación**. Cada bloque está conectado a datos reales del backend desde el primer día y termina en algo **navegable** (pantallas que se abren en el navegador) y **verificable** (pruebas automáticas y un recorrido guiado con datos reales).

<a id="indice"></a>

## Índice

1. [Decisiones técnicas y restricciones](#s1)
2. [Estado actual y tablero de avance](#s2)
3. [Estructura de carpetas](#s3)
4. [Contrato con el backend](#s4)
5. [Convenciones técnicas](#s5)
6. [Bloques de implementación](#s6)
   - [Bloque 0. Proyecto Angular, proxy y entorno](#b0)
   - [Bloque 1. Núcleo técnico y componentes base](#b1)
   - [Bloque 2. Acceso y estructura de la aplicación](#b2)
   - [Bloque 3. Usuarios](#b3)
   - [Bloque 4. Configuración, combustibles y precios](#b4)
   - [Bloque 5. Instituciones](#b5)
   - [Bloque 6. Órdenes de compra](#b6)
   - [Bloque 7. Vales](#b7)
   - [Bloque 8. Despacho y correcciones](#b8)
   - [Bloque 9. Auditoría e integridad](#b9)
   - [Bloque 10. Lectura OCR](#b10)
   - [Bloque 11. Consultas de saldo y consumo](#b11)
   - [Bloque 12. Panel, reportes y exportación](#b12)
   - [Bloque 13. Calidad, accesibilidad y rendimiento](#b13)
   - [Bloque 14. Compilación, integración y entrega](#b14)
7. [Decisiones pendientes](#s7)
8. [Cobertura de requerimientos y endpoints](#s8)

---

<a id="s1"></a>

## 1. Decisiones técnicas y restricciones

**Roles y navegación:** Administrador ve todos los módulos; Oficina ve gestión, OCR, vales, consultas y reportes; Despachador ve únicamente el flujo rápido de consumo. Las rutas se protegen en Angular por rol para orientar la navegación, y la API valida permisos en cada operación.

**Despacho entre sedes:** la pantalla de consumo permite buscar/leer un vale, ingresar galones y confirmar; presenta precio y saldo actualizado. Tras un registro exitoso refresca el saldo y el historial. Los cambios realizados en otra estación se anuncian por `GET /eventos/vales/{vale_id}` (SSE autenticado con `fetch`) y disparan una consulta REST del saldo autoritativo (objetivo: pocos segundos), con consulta al reconectar.

**OCR:** el flujo de Oficina acepta PDF e imágenes y presenta el original junto a campos extraídos por RapidOCR, confianza/advertencias y controles para corregir antes de confirmar.

**Arquitectura.** Aplicación de una sola página (SPA) en Angular 21.2.0 que vive en la **raíz del repositorio**, junto a `backend/`: `angular.json`, `package.json`, `tsconfig*.json`, `src/` y `public/` cuelgan directamente de la raíz. En producción se compila a archivos estáticos y los sirve el backend FastAPI desde el mismo origen que la API (`/api/v1`); en desarrollo, `ng serve` hace de proxy hacia el backend. Un solo origen evita CORS; la política de tokens se configura según el transporte seguro acordado con el backend.

**Restricciones acordadas y cómo se cumplen:**
- **Sin SSR:** se crea el proyecto con la opción de renderizado en servidor desactivada; la compilación es solo de navegador.
- **Sin PWA:** sin `service worker`, sin manifiesto y sin modo sin conexión. La caché la controla el servidor con cabeceras HTTP.
- **Sin state manager externo:** el estado vive en servicios propios con `signal` de Angular (sesión, catálogos, avisos), en el estado local de cada pantalla y en la URL (filtros y paginación). La fuente de verdad es la API.
- **Lista cerrada de dependencias de interfaz.** Además de lo que genera `ng new` (núcleo, router, formularios, `HttpClient`, RxJS), se autorizan explícitamente **solo** estos paquetes: **PrimeNG 21** (tabla, paginador, diálogo, avisos, combos, calendario y gráficos), **`@primeuix/themes`** (preset de tema de PrimeNG), **`primeicons`** (iconos internos que PrimeNG exige), **`iconify-icon`** (iconografía propia de la aplicación), **`chart.js`** (motor de `p-chart`) y **Tailwind 4** con **`@tailwindcss/postcss`** (maquetación). `@angular/cdk` llega como dependencia de PrimeNG y se acepta por esa vía. No se agregan Angular Material, NgRx, librerías de PDF ni de pruebas de navegador. `scripts/verificar-dependencias.mjs` compara `package.json` con la lista blanca de `docs/dependencias-base.json` y falla ante cualquier paquete fuera de ella.

**Lo que trae Angular 21.2.0 y se aprovecha:** cambio de detección sin `zone.js` por defecto (zoneless), `HttpClient` disponible desde el inicio, Vitest como ejecutor de pruebas por defecto (`ng test`), señales, control de flujo en plantillas (`@if`, `@for`, `@switch`, `@defer`) y componentes independientes (standalone). Se comprueba al crear el proyecto.

**Decisiones del frontend:**
- **Formularios reactivos tipados**, no Signal Forms: en Angular 21.2.0 Signal Forms es experimental.
- **Diálogos con `p-dialog` de PrimeNG**: aporta trampa de foco, cierre con Escape, bloqueo del fondo y API declarativa sin código propio. El diálogo de motivo obligatorio (anular, ajustar, revertir) se construye sobre él.
- **Gráficos con `p-chart` (PrimeNG sobre `chart.js`)** para barras y líneas, **siempre** acompañados de una tabla equivalente en un `<details>`: un `canvas` por sí solo no es accesible para lectores de pantalla, y el requisito de accesibilidad no se delega a la librería.
- **PDF por impresión del navegador:** el backend entrega datos en JSON; Angular los muestra en vistas preparadas para imprimir (`@media print`) y el usuario imprime o usa "Guardar como PDF".
- **Código de barras Code 128 propio en SVG** para el vale (RF-VAL-12), probado con vectores del estándar y con un lector real.
- **Iconografía con `iconify-icon`** (`<iconify-icon icon="...">`) para los iconos propios de la interfaz; `primeicons` queda solo donde PrimeNG lo usa internamente. Para que producción no dependa de la API pública de Iconify, los iconos que se usen se registran desde paquetes locales de `@iconify-json/*` en el arranque de la aplicación.
- **Estilos con Tailwind 4 para la maquetación** (rejillas, espaciado, utilidades) y el sistema de temas de PrimeNG para los componentes. El orden de capas se declara con `theme.options.cssLayer` en `providePrimeNG` (`{ name: 'primeng', order: 'theme, base, primeng' }`), que es el mecanismo oficial de interoperabilidad con Tailwind 4: así el *preflight* no pisa los estilos de PrimeNG.
- **Dinero sin `float`:** los montos llegan como cadenas decimales. El cliente nunca suma ni redondea montos; solo los muestra y hace comprobaciones informativas con enteros (`bigint`). La regla definitiva siempre la aplica el backend.
- **Fechas sin conversiones accidentales:** las fechas sin hora (`2027-03-15`) se manejan como cadenas; los instantes se muestran con el desfase fijo de Lima (`-0500`), sin depender de la zona horaria del navegador.
- **Autenticación con JWT:** access token de vida corta en memoria y refresh token rotatorio en cookie HttpOnly/Secure/SameSite si el despliegue permite cookie; nunca guardar tokens en `localStorage`. Validar reCAPTCHA v3 en el inicio de sesión; Angular no decide si el score es válido.
- **Sin pruebas de navegador automatizadas** (requieren herramientas nuevas): las pruebas son unitarias y de componentes con Vitest, una prueba de contrato contra el `openapi.json` del backend y un guion de verificación manual por bloque.

**Navegadores:** versiones actuales de Chrome, Edge, Firefox y Safari. `crypto.randomUUID()` solo existe en contextos seguros (HTTPS o `localhost`); se incluye una alternativa con `crypto.getRandomValues`.

**Fuera de este plan:** instrumentos de la tesis (encuestas, mediciones y muestra), igual que en la especificación de requerimientos.

---

<a id="s2"></a>

## 2. Estado actual y tablero de avance

### 2.1 Estado actual del proyecto

Documentación y diseño:
- [x] Especificación de requerimientos funcionales v3.0 (roles Oficina/Despachador y autenticación con reCAPTCHA/JWT)
- [x] Plan de backend v4.0 en FastAPI (15 fases; catálogo de endpoints por validar)
- [x] Stack definido: Angular 21.2.0 + PrimeNG 21 + Tailwind 4 + `iconify-icon`, FastAPI, PostgreSQL y OCR con RapidOCR
- [x] Restricciones definidas (sin SSR, PWA ni state manager; lista cerrada de dependencias de interfaz)
- [x] Plan anterior de frontend en Livewire (reemplazado por este plan)
- [ ] Bocetos de baja fidelidad validados con 2 o 3 usuarios (despacho, revisión OCR y consulta de saldo)
- [ ] Brechas del backend resueltas (sección 4.4)
- [ ] Puntos por confirmar con la estación (ver especificación y sección 7)

Implementación (según lo conversado, aún no se inicia; marca lo que ya tengas):
- [ ] Proyecto Angular creado
- [ ] Backend FastAPI levantado con datos de demostración
- [ ] Primera pantalla conectada a datos reales

### 2.2 Tablero de bloques

Avance global: **0 de 15 bloques cerrados**

Cada bloque indica la fase del backend de la que depende.

- [ ] **Bloque 0** Proyecto Angular, proxy y entorno (requiere backend Fases 0 y 1) (inicio: ____ / fin: ____)
- [ ] **Bloque 1** Núcleo técnico y componentes base (requiere Fase 2) (inicio: ____ / fin: ____)
- [ ] **Bloque 2** Acceso y estructura de la aplicación (requiere Fase 2) (inicio: ____ / fin: ____)
- [ ] **Bloque 3** Usuarios (requiere Fase 3) (inicio: ____ / fin: ____)
- [ ] **Bloque 4** Configuración, combustibles y precios (requiere Fase 4) (inicio: ____ / fin: ____)
- [ ] **Bloque 5** Instituciones (requiere Fase 5) (inicio: ____ / fin: ____)
- [ ] **Bloque 6** Órdenes de compra (requiere Fase 5) (inicio: ____ / fin: ____)
- [ ] **Bloque 7** Vales (requiere Fase 6) (inicio: ____ / fin: ____)
- [ ] **Bloque 8** Despacho y correcciones (requiere Fase 7) (inicio: ____ / fin: ____)
- [ ] **Bloque 9** Auditoría e integridad (requiere Fase 8) (inicio: ____ / fin: ____)
- [ ] **Bloque 10** Lectura OCR (requiere Fase 11) (inicio: ____ / fin: ____)
- [ ] **Bloque 11** Consultas de saldo y consumo (requiere Fase 12) (inicio: ____ / fin: ____)
- [ ] **Bloque 12** Panel, reportes y exportación (requiere Fase 12) (inicio: ____ / fin: ____)
- [ ] **Bloque 13** Calidad, accesibilidad y rendimiento (inicio: ____ / fin: ____)
- [ ] **Bloque 14** Compilación, integración y entrega (requiere Fases 13 y 14) (inicio: ____ / fin: ____)

### 2.3 Orden de trabajo sincronizado con el backend

1. El frontend avanza **una fase por detrás del backend**, siempre sobre datos reales: un bloque no empieza hasta que la fase de la que depende pasó su verificación.
2. Los bloques 0 a 2 son la base (proyecto, núcleo y acceso). Los bloques 3 a 8 forman el núcleo operativo y ya reemplazan al Excel, sin OCR.
3. El bloque 10 (OCR) depende de la Fase 11 del backend; el motor y la evaluación del OCR (Fases 9 y 10) no afectan al frontend.
4. Los bloques 13 y 14 cierran.

**Cómo conviven los dos procesos en desarrollo:** `fastapi dev` en `backend/` (puerto 8000) y `ng serve` en la raíz del repositorio (puerto 4200). Siempre se trabaja abriendo `http://localhost:4200`.

---

<a id="s3"></a>

## 3. Estructura de carpetas

```
station-jose/                        # raíz del repositorio = proyecto Angular
├── angular.json  package.json  tsconfig*.json   # los genera el CLI
├── proxy.conf.json                  # /api, /docs y /openapi.json hacia el backend (solo desarrollo)
├── contrato/
│   └── openapi.json                 # copia del contrato del backend, actualizada en cada fase
├── scripts/
│   └── verificar-dependencias.mjs   # compara package.json con la lista blanca
├── docs/
│   ├── dependencias-base.json       # lista blanca de dependencias autorizadas
│   └── guiones/                     # guion de verificación manual de cada bloque
├── public/                          # favicon y estáticos
├── backend/                         # FastAPI (plan aparte)
└── src/
    ├── index.html  main.ts  styles.css   # styles.css: capas de Tailwind + tema PrimeNG
    ├── assets/
    ├── environments/
    │   └── environment.ts           # apiUrl relativo: '/api/v1'
    └── app/
        ├── app.config.ts            # providers: router, HttpClient, PrimeNG, locale, inicializador
        ├── app.routes.ts            # rutas con carga diferida por módulo
        ├── core/                    # servicios únicos de toda la aplicación
        │   ├── api/                 # cliente.ts, endpoints.ts, errores.ts, paginacion.ts, descargas.ts
        │   ├── constants/           # tokens de inyección, claves, regex, enums fijos
        │   ├── guards/              # autenticadoGuard, permisoGuard, cambioPasswordGuard
        │   ├── interceptors/        # auth, errores, sesión
        │   ├── models/              # tipos globales: Usuario, Sesion, Pagina<T>, ErrorApi
        │   └── services/            # auth, catálogos, avisos, formato, utilidades
        ├── layouts/                 # cascarones visuales, sin lógica de negocio
        │   ├── admin/               # header + sidebar + <router-outlet>
        │   │   └── components/
        │   │       ├── header/
        │   │       └── sidebar/
        │   └── auth/                # ingreso, recuperación, restablecimiento
        ├── shared/                  # reutilizable y sin lógica de negocio
        │   ├── components/          # envoltorios de PrimeNG, badge-estado, vacio, encabezado-pagina
        │   ├── directives/          # puede (según permisos)
        │   ├── pipes/               # moneda, galones, fecha, instante
        │   ├── utils/               # uuid.ts, carga.ts, filtros-url.ts, formularios.ts
        │   └── validators/          # validadores reactivos propios
        └── features/                # un directorio por módulo, con sus propias rutas
            ├── auth/  usuarios/  configuracion/  combustibles/  instituciones/  ordenes/
            ├── vales/ despacho/  auditoria/      ocr/           consultas/      reportes/
            ├── panel/ impresion/
            └── (en cada una) *.routes.ts · *.api.ts · *.model.ts · pages/ · components/
```

**Qué va en cada carpeta.**

| Carpeta | Contenido | Regla de dependencia |
|---|---|---|
| `core/` | Servicios singleton (`providedIn: 'root'`), guardas, interceptores, modelos globales, `environment` | No importa nada de `features/` ni de `shared/` |
| `shared/` | Piezas presentacionales puras, pipes, directivas, utilidades y validadores | No importa de `features/`; no inyecta servicios de negocio |
| `features/` | Un módulo de negocio autocontenido con sus rutas, páginas, API y servicios | No importa de otro `features/`; si comparte algo, sube a `shared/` o `core/` |
| `layouts/` | Cabecera, menú y `<router-outlet>`; solo estructura visual | No conoce `features/`; usa `shared/` y `core/` |

**Convención de nombres.** Carpetas y estructura en inglés (`core/`, `shared/`, `features/`, `layouts/`), que es la convención universal de Angular y no choca con el CLI. Sufijos de archivo: `.routes.ts` (rutas del módulo), `.api.ts` (llamadas HTTP), `.model.ts` (tipos del dominio), `.store.ts` (estado con señales), `.page.ts` (componente asociado a una ruta), `.service.ts`, `.guard.ts`, `.interceptor.ts`, `.pipe.ts`, `.spec.ts`. **El dominio se nombra en español**, igual que la API y la base de datos: `vales.service.ts`, `orden-compra.model.ts`, `precio_galon`. Los controles de formulario llevan exactamente el nombre del campo de la API para que los `422` se asignen solos (sección 4.1).

---

<a id="s4"></a>

## 4. Contrato con el backend

El frontend consume los endpoints definidos del catálogo de `plan-implementacion-backend-fastapi.md` (sección 5). Cada bloque lista los que usa; la sección 8 comprueba que ninguno queda sin consumir.

### 4.1 Convenciones de la API que Angular respeta

- **Prefijo:** todo bajo `/api/v1`, relativo al origen (nunca una URL absoluta, para que el soporte de XSRF de `HttpClient` funcione).
- **Autenticación:** access JWT en memoria y refresh rotatorio en cookie HttpOnly/Secure/SameSite; nunca tokens en localStorage. Protección CSRF/origen en renovación y cierre. reCAPTCHA v3 se ejecuta en login y el token va al backend.
- **Paginación:** `?pagina=1&por_pagina=15` y respuesta `{ items, total, pagina, por_pagina }`.
- **Errores:** `{ codigo, mensaje, detalles }`. En un `422`, `detalles` lista cada campo con su mensaje.
- **Nombres de campos:** los controles de cada formulario se llaman igual que los campos de la API (`precio_galon`, `fecha_emision`, ...). Así los errores `422` se asignan solos al control correcto.
- **Montos y cantidades:** cadenas decimales. **Fechas:** `AAAA-MM-DD`; **instantes:** ISO 8601 con desfase `-05:00`.
- **Descargas:** `.xlsx` y documentos con `HttpClient` en modo `blob`; si la respuesta es un error, el cuerpo JSON se interpreta igual que cualquier otro error de la API.

### 4.2 Rutas de la aplicación

- Acceso: `/ingresar`, `/recuperar`, `/restablecer/:token`, `/cambiar-password`, `/acceso-denegado`.
- Panel: `/panel`.
- Administración: `/usuarios`, `/configuracion/parametros`, `/configuracion/estacion`, `/combustibles`, `/combustibles/:id/precios`.
- Instituciones: `/instituciones`, `/instituciones/:id`.
- Órdenes y vales: `/ordenes`, `/ordenes/nueva`, `/ordenes/:id`, `/ordenes/:id/editar`, `/ordenes/:id/vales/emitir`, `/ordenes/:id/vales/entidad`, `/vales`, `/vales/:id`.
- Despacho: `/despacho`.
- OCR: `/ocr/nueva`, `/ocr/:id/revision`, `/ocr/historial`.
- Consultas: `/consultas/saldo`, `/consultas/consumo`, `/consultas/estado-cuenta/:institucionId`.
- Reportes: `/reportes/consumo`, `/reportes/ordenes`.
- Auditoría: `/auditoria/bitacora`, `/auditoria/integridad`.
- Impresión (sin menú): `/imprimir/vale/:id`, `/imprimir/comprobante/:movimientoId`, `/imprimir/reporte/:tipo`.
- Solo en desarrollo: `/diagnostico`, `/componentes`.

### 4.3 Permisos en la interfaz

- Administrador: todos los módulos.
- Oficina: usuarios no; sí instituciones, órdenes, OCR, combustibles/precios, vales, consultas y reportes. Auditoría administrativa/configuración avanzada solo Administrador.
- Despachador: únicamente `/despacho`; puede buscar vale, registrar consumo e imprimir/consultar la confirmación de su propio movimiento. No hay enlaces ni acceso directo a módulos administrativos. La API debe responder 403 aunque se altere la ruta o el menú.

Los permisos llegan en `GET /auth/yo` (`sesion`, `usuarios.gestionar`, `ordenes.editar`, ...). El menú, las guardas de ruta y los botones de acción se habilitan con esas cadenas; las mismas del backend (sección 4.1 de su plan). La interfaz solo oculta lo que no se puede usar; la autorización real siempre ocurre en el servidor y un `403` se muestra como "acceso denegado".

### 4.4 Brechas del plan de backend que este plan requiere

El catálogo de endpoints del backend define las pantallas; la cobertura se confirmará al actualizar el contrato OpenAPI. Faltan estas piezas de apoyo, que deben existir en la fase indicada para poder verificar los bloques del frontend con datos reales:

- [ ] **G1. Datos de demostración completos** (Fases 4 a 7): `python -m app.cli sembrar-demo` debe crear, además de los catálogos, tres usuarios (administrador, Oficina y Despachador) con la contraseña conocida de demostración y sin cambio obligatorio (solo con `ENTORNO=desarrollo`), instituciones con las dos modalidades de numeración, órdenes en distintos estados, vales de la estación y de entidad, y consumos.
- [ ] **G2. Exportar el contrato desde la Fase 1:** `python -m app.cli exportar-openapi` escribe `backend/openapi.json`; se copia a `contrato/` (raíz del repositorio) al cerrar cada fase del backend (hoy el plan lo guarda recién en la Fase 13).
- [ ] **G3. Campos mínimos en las respuestas**, para no encadenar peticiones por cada fila:
  - listado de instituciones y búsquedas: `modalidad_numeracion`;
  - listado y detalle de órdenes: nombre y RUC de la institución;
  - listados y detalle de vales: código interno, número de la entidad, nombre de la institución, número de la orden, combustible, saldo y estado;
  - movimientos de vale: nombre del usuario;
  - detalle de orden: lista resumida de vales (código, cantidad, saldo, estado);
  - `POST /vales/{id}/impresion`: `es_duplicado` y el valor para el código de barras.
- [ ] **G4. Errores con `detalles` útiles:** `SALDO_INSUFICIENTE` incluye `saldo`; `PRESUPUESTO_EXCEDIDO` incluye `presupuesto_restante` y `maximo_galones`; `CUENTA_BLOQUEADA` incluye los minutos de espera; `NUMERO_FUERA_DE_SERIE` incluye el rango; `ORDEN_POSIBLE_DUPLICADA` incluye el identificador y el número de la orden coincidente.
- [ ] **G5. Registro de extracción fallida confirmable:** `POST /ocr/extracciones/{id}/confirmar` debe aceptar una extracción en estado `fallida` (registro manual con el archivo ya subido), según RF-OCR-09.

---

<a id="s5"></a>

## 5. Convenciones técnicas

**Angular:**
- Solo componentes independientes (standalone), con `ChangeDetectionStrategy.OnPush` y sin dependencia de `zone.js`.
- Estado con `signal`, `computed` y `effect` (este último solo para efectos externos, nunca para derivar datos). Entradas y salidas con `input()`, `output()` y `model()`.
- Plantillas con `@if`, `@for` (siempre con `track`), `@switch` y `@defer` (gráficos y pantallas pesadas).
- Inyección con `inject()`. Guardas e interceptores como funciones.
- TypeScript en modo estricto, sin `any`, con interfaces para cada respuesta de la API (modelos escritos a mano a partir del contrato).
- Formularios reactivos tipados (`FormGroup`, `FormControl`, `FormArray`); validaciones del cliente solo informativas.
- Rutas con carga diferida (`loadChildren` o `loadComponent`) por módulo y títulos por ruta.
- Cada ruta de listado guarda sus filtros, orden y página en los parámetros de la URL (recargar o compartir la dirección reproduce la vista).

**Datos y estado:**
- Un archivo `*.api.ts` por módulo con una función por endpoint, que devuelve `Observable` tipado. Las rutas salen de `core/api/endpoints.ts` (un registro único), que la prueba de contrato compara con `contrato/openapi.json`.
- `crearCarga(fuente$)`: utilidad propia que devuelve señales `datos`, `cargando` y `error`, y cancela la petición anterior al cambiar la fuente (`switchMap`).
- Servicios con señales solo para lo transversal: `AuthStore`, `CatalogosStore` y `AvisosStore`. Todo lo demás vive en la pantalla que lo usa.
- Ninguna pantalla consulta dos veces lo mismo: lo que viene en la respuesta de un listado no se vuelve a pedir por fila.

**Interfaz y accesibilidad:**
- Estados explícitos en cada pantalla: cargando, vacío, error y éxito.
- Todo botón que ejecuta una acción con efecto (emitir, consumir, anular, confirmar) se deshabilita mientras la petición está en curso.
- Anular, ajustar y revertir exigen un diálogo con motivo obligatorio.
- Errores `422` junto al campo; el resto, como aviso con región `aria-live`.
- Estado y confianza con color **y** texto. Contraste de texto de al menos 4.5 a 1.
- Teclado completo, foco visible, foco al encabezado de la página tras navegar, título del documento por ruta.
- Cantidades con `inputmode="decimal"`, 2 decimales y formato `S/ 1,234.56` para soles y `1,234.56 gal` para galones (configuración regional `es-PE`).
- Diseño adaptable (360, 768 y 1280 píxeles de ancho como mínimo).

**Pruebas (Vitest, con `ng test`):**
- Unitarias de funciones puras (dinero, fechas, código de barras, utilidades).
- De componentes y servicios con `HttpTestingController`, usando respuestas con la misma forma que el contrato.
- De contrato: todo endpoint del registro existe en `contrato/openapi.json` con el mismo método.

**Git:** ramas y prefijos de commit como en el backend. Etiqueta por bloque cerrado (`b05-cerrado`).

**Definición de terminado de un bloque:**
- [ ] Todas las tareas del bloque marcadas
- [ ] `ng test` en verde y `ng build` sin errores ni advertencias nuevas
- [ ] `node scripts/verificar-dependencias.mjs` sin cambios
- [ ] Verificación del bloque ejecutada con datos reales y anotada en `docs/guiones/`
- [ ] Sin datos fijos en las pantallas, sin `any` y sin lógica de negocio en el cliente
- [ ] Commit y etiqueta creados

[↑ Volver al índice](#indice)

---

<a id="s6"></a>

## 6. Bloques de implementación

**Estructura de cada bloque:** objetivo, requerimientos, rutas, endpoints que consume, tareas, entregable **navegable** y **verificación**.

**Reglas permanentes:**
- Ninguna pantalla usa datos fijos: todo viene del backend (con `sembrar-demo` para desarrollo).
- Los componentes de pantalla no contienen reglas de negocio: recogen datos, llaman al backend y muestran el resultado o el error.
- Cada formulario nombra sus controles igual que los campos de la API y muestra los errores `422` junto al campo.
- Ninguna dependencia fuera de la lista blanca de `docs/dependencias-base.json`.

---

<a id="b0"></a>

### Bloque 0. Proyecto Angular, proxy y entorno

**Objetivo:** proyecto creado con las restricciones aplicadas y conectado al backend.
**Requiere backend:** Fases 0 y 1 (entorno, esqueleto y `GET /salud`).
**Requerimientos:** ninguno directo (base).
**Rutas:** `/` (pantalla de arranque).

**Endpoints que consume:**
- `GET /salud`: estado del backend, de PostgreSQL y de RapidOCR.

Tareas:
- [ ] Instalar la versión de Node.js que exija Angular 21.2.0 y la CLI de Angular (`ng version` muestra las versiones).
- [ ] Proyecto Angular **en la raíz del repositorio** (junto a `backend/`), creado con `ng new`, con enrutamiento, hojas de estilo CSS, **sin SSR ni prerenderizado** y con las opciones por defecto de Angular 21.2.0 (sin `zone.js`, Vitest).
- [ ] Instalar y configurar la capa de interfaz: `primeng`, `@primeuix/themes`, `primeicons`, `iconify-icon`, `chart.js` y `tailwindcss` + `@tailwindcss/postcss`. `app.config.ts` registra `providePrimeNG` con el preset de tema y `theme.options.cssLayer = { name: 'primeng', order: 'theme, base, primeng' }`.
- [ ] Registrar los iconos de `iconify-icon` que use la aplicación desde paquetes locales de `@iconify-json/*`, para no depender de la API pública de Iconify en producción.
- [ ] Guardar la lista blanca de dependencias en `docs/dependencias-base.json` y escribir `scripts/verificar-dependencias.mjs`: lee `package.json` y `docs/dependencias-base.json` y falla si aparece un paquete fuera de la lista autorizada (sección 1).
- [ ] Revisar `tsconfig.json`: `strict` activo y `strictTemplates` activo.
- [ ] `proxy.conf.json` con `/api`, `/docs` y `/openapi.json` hacia `http://127.0.0.1:8000`, y `proxyConfig` en `angular.json`. Con `/docs` por el proxy, se puede iniciar sesión desde la documentación del backend y compartir la sesión con la aplicación en `localhost:4200`.
- [ ] `index.html` con `lang="es"` y título; registrar los datos de idioma `es-PE` (`registerLocaleData`) y `LOCALE_ID`.
- [ ] Pantalla de arranque que consulta `GET /salud` y muestra el estado de cada componente del backend.
- [ ] Una prueba del componente con `HttpTestingController`.
- [ ] README del frontend: cómo arrancar los dos procesos y qué puertos usan.

**Entregable navegable:** `http://localhost:4200` muestra "Backend: ok · PostgreSQL: ok · RapidOCR: 5.x".

**Verificación:**
- Con el backend en marcha: `ng serve` y abrir `http://localhost:4200`; ver los tres estados en `ok`. Con el backend apagado, ver un mensaje de error claro y no una pantalla en blanco.
- `ng test` y `ng build` terminan sin errores.
- `node scripts/verificar-dependencias.mjs` termina con código 0.
- `http://localhost:4200/docs` abre la documentación interactiva del backend.

---

<a id="b1"></a>

### Bloque 1. Núcleo técnico y componentes base

**Objetivo:** la base técnica sobre la que se construyen todas las pantallas.
**Requiere backend:** Fase 2 (sesión) para verificar con sesión real; `exportar-openapi` (G2).
**Requerimientos:** ninguno directo (base de todos).
**Rutas:** `/diagnostico` y `/componentes` (solo en desarrollo).

**Endpoints que consume:**
- `GET /catalogos/enums`: estados, tipos, emisores, modalidades, roles y permisos.

Tareas:
- [ ] `app.config.ts`: `provideRouter` con enlace de parámetros a entradas de componentes, restauración de la posición de desplazamiento y títulos por ruta; `provideHttpClient` con interceptor para Bearer access JWT y renovación controlada ante 401; `LOCALE_ID` `es-PE`.
- [ ] `core/api/errores.ts`: clase `ErrorApi` (`estado`, `codigo`, `mensaje`, `detalles`) y `erroresInterceptor` que convierte cualquier `HttpErrorResponse` (incluida una respuesta `blob` con JSON y la falta de red, con código `ERROR_RED`) en un `ErrorApi`.
- [ ] `core/api/endpoints.ts`: registro único de endpoints (método y ruta) y `ClienteApi` con `get`, `post`, `put`, `patch`, y el tipo `Pagina<T>`.
- [ ] `core/api/descargas.ts`: descarga de archivos desde un `blob` (`.xlsx`).
- [ ] `shared/utils/dinero.ts`: convierte cadenas decimales a `bigint` (centésimas), compara y valida formato (hasta 2 decimales). Sin `Number` para montos.
- [ ] `shared/utils/fechas.ts`: `hoyLima()` con desfase fijo, formatos `dd/mm/aaaa` y `dd/mm/aaaa hh:mm` desde cadenas, sin pasar por `Date` las fechas sin hora. Pipes en `shared/pipes/`: `moneda`, `galones`, `fecha` e `instante`.
- [ ] `shared/utils/`: `uuid.ts` (con alternativa fuera de contexto seguro), `carga.ts` (`crearCarga`), `filtros-url.ts` (filtros enlazados a la URL) y `formularios.ts` (`aplicarErroresServidor(form, error)`, que asigna los `detalles` de un `422` a los controles).
- [ ] `core/services/catalogos.store.ts`: señales con las listas de `GET /catalogos/enums` y funciones para obtener la etiqueta de cada valor.
- [ ] Componentes de `shared/components/`: envoltorios delgados sobre PrimeNG (`Tabla`, `Paginador`, `Dialogo` sobre `p-dialog`, `Combobox` sobre `p-select`, `ConfirmarMotivo`) y propios donde PrimeNG no aplica (`AvisosStore` con su región `aria-live`, `Campo` con etiqueta/ayuda/errores, `CampoCantidad` con `inputmode="decimal"`, `BadgeEstado` que combina color **y** texto, `Cargando`, `Vacio`, `EncabezadoPagina`, `TemporizadorEspera`). Ningún componente de `shared/` inyecta servicios de negocio.
- [ ] `styles.css`: Tailwind 4 con `@theme` para los tokens de diseño (la paleta corporativa azul ya está definida desde el isotipo), capas de PrimeNG en el orden acordado, estilos de foco, adaptación a pantallas pequeñas y reglas base de `@media print`.
- [ ] Pantalla `/componentes`: galería con todos los componentes y sus estados. Pantalla `/diagnostico`: estado del backend y las listas de `GET /catalogos/enums`.
- [ ] Pruebas: dinero (comparaciones, ceros, redondeo no permitido), fechas (`hoyLima`, formatos), `crearCarga` (cancela la petición anterior), `aplicarErroresServidor`, interceptor de errores, y la prueba de contrato contra `contrato/openapi.json`.

**Entregable navegable:** `/componentes` y `/diagnostico`.

**Verificación:**
- `ng test` en verde, incluida la prueba de contrato (falla si un endpoint del registro no existe en el contrato).
- Abrir `/componentes` y recorrer cada componente solo con el teclado (diálogo: se abre, atrapa el foco y se cierra con Escape).
- Iniciar sesión en `http://localhost:4200/docs` (Authorize y `POST /auth/login`) y abrir `/diagnostico`: se ven las listas de `GET /catalogos/enums`. Sin sesión, se ve el error de la API como mensaje, no una pantalla rota.

---

<a id="b2"></a>

### Bloque 2. Acceso y estructura de la aplicación

**Objetivo:** inicio y cierre de sesión, cambio obligatorio de contraseña, expiración por inactividad y la estructura de la aplicación con menú por permisos.
**Requiere backend:** Fase 2.
**Requerimientos:** AUT-01 a AUT-10.
**Rutas:** `/ingresar`, `/recuperar`, `/restablecer/:token`, `/cambiar-password`, `/acceso-denegado`, `/panel` (provisional).

**Endpoints que consume:**
- `POST /auth/login`: inicio de sesión.
- `POST /auth/logout`: cierre de sesión.
- `GET /auth/yo`: usuario actual, rol, permisos e indicador de cambio obligatorio.
- `POST /auth/recuperar`: solicitud de enlace de recuperación.
- `POST /auth/restablecer`: contraseña nueva con el token.
- `POST /auth/cambiar-password`: cambio de contraseña.

Tareas:
- [ ] `AuthStore` con señales (`usuario`, `permisos`, `autenticado`, `debeCambiarPassword`) y `puede(permiso)`; carga inicial con `provideAppInitializer` que llama a `GET /auth/yo` (un `401` significa "sin sesión", no un error).
- [ ] Guardas funcionales: `autenticadoGuard` (lleva a `/ingresar?retorno=...`), `permisoGuard(permiso)` (lleva a `/acceso-denegado`) y `cambioPasswordGuard` (lleva a `/cambiar-password` mientras sea obligatorio).
- [ ] Interceptor de sesión: ante un `401` con `SESION_EXPIRADA`, guarda la ruta actual, limpia el estado y lleva a `/ingresar` con el aviso "Su sesión expiró"; tras volver a ingresar, regresa a la pantalla en la que estaba. Ante un `403` con `CAMBIO_PASSWORD_OBLIGATORIO`, lleva a `/cambiar-password`.
- [ ] Pantalla de ingreso: correo y contraseña con los atributos `autocomplete` para gestores de contraseñas; mensaje genérico ante credenciales inválidas; mensaje con el tiempo de espera ante `CUENTA_BLOQUEADA`.
- [ ] Pantallas de recuperación (siempre el mismo mensaje, exista o no el correo), de restablecimiento con el token de la URL y de cambio de contraseña (contraseña actual, nueva de al menos 8 caracteres y distinta de la actual, validación informativa).
- [ ] Cierre de sesión que limpia el estado y lleva a `/ingresar`.
- [ ] Estructura principal (`layouts/admin/`): cabecera con el nombre de la estación y el usuario, menú lateral definido por una tabla de configuración (ruta, etiqueta, permiso requerido), que se colapsa en pantallas pequeñas; región de avisos; enfoque en el encabezado de la página tras navegar; título del documento por ruta.
- [ ] Directiva `puede` (o `@if (auth.puede(...))`) para ocultar acciones sin permiso.
- [ ] Cargar `CatalogosStore` justo después de iniciar sesión.
- [ ] Pantalla de acceso denegado y pantalla provisional de `/panel`.
- [ ] Pruebas: formulario de ingreso (errores y bloqueo), guardas (redirecciones con retorno), interceptor (401 y 403), menú por rol, cambio obligatorio.

**Entregable navegable:** de `/ingresar` a un `/panel` con el menú del rol.

**Verificación:**
- Con el administrador creado por `crear-admin`: ingresar con la contraseña temporal, ser llevado a `/cambiar-password`, cambiarla y llegar al panel; cerrar sesión.
- Contraseña errónea: mensaje genérico. Cinco intentos fallidos: mensaje de bloqueo con el tiempo de espera.
- Recuperación: solicitar el enlace; copiar de la consola del backend el enlace de desarrollo y completar el restablecimiento; el enlace no funciona una segunda vez.
- Expiración: en PostgreSQL (por ejemplo, desde pgAdmin), atrasar `ultimo_uso` de la sesión; la siguiente acción lleva a `/ingresar` con el aviso y, al ingresar, regresa a la pantalla anterior.
- `ng test` y `ng build` en verde.

---

<a id="b3"></a>

### Bloque 3. Usuarios

**Objetivo:** administración de cuentas y roles.
**Requiere backend:** Fase 3.
**Requerimientos:** USR-01 a USR-07.
**Rutas:** `/usuarios`.

**Endpoints que consume:**
- `GET /usuarios`: listado con búsqueda y filtros.
- `POST /usuarios`: alta; devuelve la contraseña temporal una sola vez.
- `GET /usuarios/{id}`: detalle para edición.
- `PATCH /usuarios/{id}`: cambio de nombre, correo o rol.
- `POST /usuarios/{id}/desactivar`: bloqueo del acceso.
- `POST /usuarios/{id}/activar`: reactivación.
- `POST /usuarios/{id}/restablecer-password`: contraseña temporal nueva.

Tareas:
- [ ] Listado con búsqueda por nombre o correo, filtros por rol y estado (en la URL) y paginación.
- [ ] Diálogo de alta y edición (nombre, correo, rol desde `CatalogosStore`) con errores `422` junto al campo.
- [ ] Diálogo que muestra la contraseña temporal **una sola vez**, con botón de copiar y advertencia de que no se podrá ver de nuevo.
- [ ] Acciones de activar, desactivar y restablecer contraseña, con confirmación.
- [ ] Mensaje explicativo ante `ULTIMO_ADMINISTRADOR`; el usuario actual no puede desactivarse a sí mismo desde la interfaz.
- [ ] Pruebas de componentes: alta, correo duplicado, cambio de rol, desactivación, contraseña temporal visible una sola vez.

**Entregable navegable:** `/usuarios` con usuarios reales.

**Verificación:**
- Crear un usuario Despachador y copiar su contraseña temporal; iniciar sesión con él en una ventana privada: el menú no muestra opciones de administración y `/usuarios` lleva a acceso denegado.
- Desactivar a ese usuario Despachador desde el administrador: su siguiente acción lo lleva a `/ingresar`.
- Intentar desactivar al único administrador: se ve el mensaje del backend.
- `ng test` en verde.

---

<a id="b4"></a>

### Bloque 4. Configuración, combustibles y precios

**Objetivo:** parámetros, datos de la estación, catálogo de combustibles y precio por galón (D-01).
**Requiere backend:** Fase 4.
**Requerimientos:** CFG-01, CFG-02, CMB-01 a CMB-04.
**Rutas:** `/configuracion/parametros`, `/configuracion/estacion`, `/combustibles`, `/combustibles/:id/precios`.

**Endpoints que consume:**
- `GET /configuracion/parametros`: valor, valor por defecto, tipo, rango y descripción de cada parámetro.
- `PUT /configuracion/parametros`: guardado en conjunto.
- `GET /configuracion/estacion`: datos de la estación.
- `PUT /configuracion/estacion`: actualización de los datos.
- `POST /configuracion/estacion/logo`: carga del logo.
- `GET /configuracion/estacion/logo`: imagen del logo.
- `GET /combustibles`: catálogo con el precio vigente de cada uno.
- `POST /combustibles`: alta de un combustible.
- `PATCH /combustibles/{id}`: cambio de nombre o estado.
- `GET /combustibles/{id}/precios`: histórico de precios.
- `POST /combustibles/{id}/precios`: registro de un precio con fecha de vigencia.
- `GET /combustibles/{id}/precio-vigente`: precio a una fecha dada.

Tareas:
- [ ] Pantalla de parámetros construida a partir de los metadatos de `GET /configuracion/parametros` (un control por parámetro según tipo, mínimo y máximo, con descripción y valor por defecto), guardado en conjunto y errores por parámetro.
- [ ] Pantalla de datos de la estación: nombre, RUC y dirección, y carga del logo con vista previa (PNG o JPG, hasta 1 MB, comprobación informativa) y actualización de la imagen tras guardar.
- [ ] Catálogo de combustibles: lista con precio vigente, alta, edición del nombre y activar o desactivar (un tipo en uso no se elimina).
- [ ] Pantalla de precios por combustible: histórico del más reciente al más antiguo con quién lo registró, formulario de nuevo precio (`precio_galon` con 2 decimales y `vigente_desde` con valor inicial de hoy), mensaje claro si la fecha es anterior al último precio, y una consulta del precio vigente a una fecha.
- [ ] Pruebas: parámetros (validación de rango y errores por clave), precio (formato de cantidad, errores del backend), carga de logo con tipo no permitido.

**Entregable navegable:** configuración, catálogo y precios gestionables.

**Verificación:**
- Registrar un precio nuevo para Diésel B5 con la fecha de hoy: aparece primero en el histórico y `precios:vigentes` del backend (o `GET /combustibles`) coincide.
- Cambiar `login_intentos_max` a 3 y comprobar en la pantalla de ingreso que el bloqueo ocurre al tercer intento; devolverlo a 5.
- Subir un logo válido y uno inválido (error claro).
- `ng test` en verde.

---

<a id="b5"></a>

### Bloque 5. Instituciones

**Objetivo:** registro y consulta de instituciones, con validación de RUC en vivo y modalidad de numeración (D-02).
**Requiere backend:** Fase 5.
**Requerimientos:** INS-01 a INS-05.
**Rutas:** `/instituciones`, `/instituciones/:id`.

**Endpoints que consume:**
- `GET /instituciones`: listado con búsqueda y filtros.
- `GET /instituciones/ruc/{ruc}`: validez del RUC e institución existente.
- `POST /instituciones`: alta.
- `GET /instituciones/{id}`: ficha con resumen.
- `PATCH /instituciones/{id}`: edición.
- `POST /instituciones/{id}/desactivar`: inhabilitación.
- `POST /instituciones/{id}/reactivar`: reactivación.

Tareas:
- [ ] Listado con búsqueda por nombre o RUC, filtros por estado y tipo (en la URL) y paginación.
- [ ] Formulario de alta y edición (diálogo o página): nombre, RUC, tipo, teléfono, correo, dirección, representante y `modalidad_numeracion` con texto de ayuda sobre qué significa cada una.
- [ ] Validación del RUC en vivo: al completar 11 dígitos, consulta `GET /instituciones/ruc/{ruc}`; muestra "RUC inválido" o un enlace a la institución existente.
- [ ] Ficha de la institución: datos, tarjetas de resumen (órdenes, saldo vigente y consumo del mes), enlaces a sus órdenes (`/ordenes?institucion_id=`), sus vales y su estado de cuenta.
- [ ] Desactivar y reactivar (administrador), con confirmación.
- [ ] Componente `ComboboxInstitucion` reutilizable (búsqueda con retardo sobre `GET /instituciones?q=&estado=activa`, teclado y ARIA), que devuelve la institución con su modalidad de numeración.
- [ ] Pruebas: RUC inválido, RUC duplicado, modalidad, permisos por rol, combobox.

**Entregable navegable:** instituciones reales gestionables, con ficha.

**Verificación:**
- Crear una institución con un RUC de dígito verificador inválido: se rechaza al escribirlo. Crear otra con numeración por orden.
- Intentar crear una con un RUC existente: aparece el enlace a la existente.
- Abrir la ficha de una institución del `sembrar-demo` y comprobar que los datos coinciden con `GET /instituciones/{id}`.
- Desactivar una institución y comprobar que ya no aparece en el combobox de órdenes (B6).
- `ng test` en verde.

---

<a id="b6"></a>

### Bloque 6. Órdenes de compra

**Objetivo:** registrar, seguir, cerrar y anular órdenes con presupuesto en soles y documento original.
**Requiere backend:** Fase 5.
**Requerimientos:** ORD-01 a ORD-11.
**Rutas:** `/ordenes`, `/ordenes/nueva`, `/ordenes/:id`, `/ordenes/:id/editar`.

**Endpoints que consume:**
- `GET /ordenes`: listado con filtros.
- `GET /ordenes/posible-duplicado`: advertencia previa de duplicado.
- `POST /ordenes`: alta de la orden.
- `GET /ordenes/{id}`: detalle.
- `PATCH /ordenes/{id}`: edición controlada.
- `POST /ordenes/{id}/archivo`: carga del documento original.
- `GET /ordenes/{id}/archivo`: documento original para el visor.
- `POST /ordenes/{id}/marcar-vigente`: paso de borrador a vigente.
- `POST /ordenes/{id}/cerrar`: cierre.
- `POST /ordenes/{id}/anular`: anulación con motivo.
- `GET /ordenes/{id}/serie`: rango autorizado, números usados y disponibles.

Tareas:
- [ ] Listado con filtros por institución (combobox), estado, rango de fechas y número, orden por fecha descendente, todo en la URL, y paginación.
- [ ] Formulario de orden (alta y edición): `ComboboxInstitucion`, número, fecha (no futura), presupuesto en soles (`CampoCantidad`), combustible (solo activos), observaciones; campos de serie (`serie_desde` y `serie_hasta`) visibles solo si la institución elegida usa numeración por orden; botones "Guardar como borrador" y "Guardar como vigente".
- [ ] Adjuntar el documento original: selección de archivo con comprobación informativa de tipo y tamaño; secuencia de dos pasos (crear la orden y luego subir el archivo), y si la carga falla, la orden queda creada y se ofrece reintentar la carga.
- [ ] Posible duplicado: consulta previa con `GET /ordenes/posible-duplicado` al completar institución, presupuesto y fecha, y manejo de `ORDEN_POSIBLE_DUPLICADA` con un diálogo que enlaza a la orden coincidente y permite continuar o cancelar.
- [ ] Edición controlada: con vales emitidos, el formulario deshabilita todo salvo observaciones y adjuntos, e indica el motivo; solo se envían los campos modificados (`PATCH`).
- [ ] Detalle de la orden: tarjetas con presupuesto, emitido en soles y galones, presupuesto restante y consumo; tabla de vales (de la respuesta del detalle) con estado y saldo; panel de serie; visor del documento original (`VisorDocumento`: `<iframe>` para PDF con la URL sellada solo para la ruta propia del backend, `<img>` con zoom para imágenes, enlace para abrir en otra pestaña); acciones de marcar vigente, cerrar (confirmación) y anular (administrador, con motivo; mensaje ante `ORDEN_CON_CONSUMOS`).
- [ ] Marcadores de inicio y fin de la tarea de registro (hooks vacíos y documentados) por si se requiere medir tiempos.
- [ ] Pruebas: número duplicado, advertencia de duplicado con confirmación, edición restringida, anulación con consumos, visibilidad de acciones por rol.

**Entregable navegable:** el flujo completo de registro manual de una orden con su documento.

**Verificación:**
- Registrar una orden en `/ordenes/nueva` con un PDF; abrir su detalle y ver el documento; repetir el número y ver el aviso del backend.
- Registrar otra con la misma institución, monto y fecha: aparece el diálogo de posible duplicado y se puede continuar.
- Cerrar la orden; como Oficina, comprobar que no aparece el botón de anular; como administrador, anular una orden sin consumos y ver el rechazo para una con consumos.
- Recargar `/ordenes?estado=vigente&institucion_id=...`: se conservan los filtros.
- `ng test` en verde.

---

<a id="b7"></a>

### Bloque 7. Vales

**Objetivo:** emitir vales con conversión de galones a soles (D-01), registrar vales de entidad (D-02), consultarlos e imprimirlos.
**Requiere backend:** Fase 6.
**Requerimientos:** VAL-01 a VAL-07, VAL-12 a VAL-15, CON-12.
**Rutas:** `/ordenes/:id/vales/emitir`, `/ordenes/:id/vales/entidad`, `/vales`, `/vales/:id`, `/imprimir/vale/:id`.

**Endpoints que consume:**
- `POST /ordenes/{orden_id}/vales/simulacion`: vista previa de la emisión sin guardar.
- `POST /ordenes/{orden_id}/vales`: emisión de uno o varios vales.
- `POST /ordenes/{orden_id}/vales-entidad`: registro de un vale de entidad.
- `GET /vales`: listado con filtros.
- `GET /vales/buscar`: búsqueda con candidatos.
- `GET /vales/alertas`: saldo bajo y próximos a vencer.
- `GET /vales/{id}`: detalle del vale.
- `GET /vales/{id}/movimientos`: línea de tiempo.
- `POST /vales/{id}/impresion`: registro de la impresión.

Tareas:
- [ ] Pantalla de emisión: carga el detalle de la orden, combustible, `FormArray` de cantidades (agregar y quitar filas) y fecha de vencimiento opcional.
- [ ] Vista previa en vivo con `POST .../vales/simulacion` (con retardo y cancelando la petición anterior): precio vigente, valor en soles, presupuesto restante y máximo de galones emisibles. Mensaje para `SIN_PRECIO_VIGENTE` (con enlace al catálogo de precios si el usuario es administrador) y para `PRESUPUESTO_EXCEDIDO` (con los valores de `detalles`).
- [ ] Resumen antes de confirmar ("3 vales de 100 galones") y emisión con `POST .../vales`; la operación es atómica, de modo que ante un error no se muestra ningún vale como emitido.
- [ ] Pantalla de vale de entidad: número de la entidad, combustible, cantidad y vencimiento; panel de serie (`GET /ordenes/{id}/serie` del Bloque 6) con números usados y disponibles; mensajes para `NUMERO_ENTIDAD_DUPLICADO`, `NUMERO_FUERA_DE_SERIE` y `SERIE_AGOTADA`.
- [ ] Listado de vales: búsqueda por código interno o número de la entidad, filtros por institución, orden, estado, combustible y emisor (en la URL), paginación, y una franja de alertas (`GET /vales/alertas`) con enlace al listado filtrado.
- [ ] Detalle del vale: código interno, número de la entidad, orden, cantidad inicial, consumido, saldo, precio aplicado, valor en soles y estado; línea de tiempo de movimientos (`GET /vales/{id}/movimientos`) con cantidad, saldo posterior, usuario, fecha y motivo.
- [ ] Componente `CodigoBarras128`: codificación Code 128 (conjunto B) y dibujo en SVG, con su suma de verificación; pruebas con vectores del estándar.
- [ ] Vista de impresión `/imprimir/vale/:id` con el encabezado de la estación (datos y logo), los datos del vale y el código de barras; el botón "Imprimir" llama a `POST /vales/{id}/impresion` (registra la impresión) y luego a `window.print()`; si el vale ya se imprimió, se muestra la marca de duplicado.
- [ ] Reglas de impresión (`@media print`): sin menú ni botones, tamaño de página y márgenes definidos.
- [ ] Pruebas: simulación y errores, emisión múltiple, número repetido, serie agotada, codificación Code 128, marca de duplicado.

**Entregable navegable:** emitir vales de una orden, registrar vales de entidad, listarlos, ver su historial e imprimirlos.

**Verificación:**
- Con una orden vigente: simular una emisión y ver precio, valor y presupuesto restante; emitir 2 vales; intentar uno que exceda el presupuesto y ver el máximo de galones del backend.
- Registrar un vale de entidad con un número repetido en una institución con numeración general: aparece el rechazo; el mismo número en otra orden con numeración por orden se acepta.
- Abrir un vale, ver su línea de tiempo con la emisión, e imprimirlo: el código de barras se lee con un lector o con la cámara de un teléfono y devuelve el código interno; la segunda impresión muestra la marca de duplicado.
- `ng test` en verde (incluida la codificación del código de barras).

---

<a id="b8"></a>

### Bloque 8. Despacho y correcciones

**Objetivo:** registrar consumos de forma rápida y segura, y corregirlos de forma trazable.
**Requiere backend:** Fase 7.
**Requerimientos:** CON-01 a CON-14, VAL-08 a VAL-11.
**Rutas:** `/despacho`, `/vales/:id` (acciones de administrador), `/imprimir/comprobante/:movimientoId`.

**Endpoints que consume:**
- `POST /vales/{id}/consumos`: registro del consumo con `token_operacion`.
- `GET /vales/{id}/consumos`: consumos del vale con filtro de fechas.
- `POST /consumos/{movimiento_id}/revertir`: reversión de un consumo.
- `GET /consumos/{movimiento_id}/comprobante`: datos del comprobante.
- `POST /vales/{id}/anular`: anulación del vale.
- `POST /vales/{id}/ajustes`: ajuste excepcional de saldo.
- `POST /vales/vencimientos/procesar`: marcar vales vencidos a demanda.

Tareas:
- [ ] Pantalla `/despacho`: campo de código con foco automático, compatible con un lector de código de barras que escribe como teclado (Enter lanza la búsqueda con `GET /vales/buscar`). Si hay un solo resultado, se elige solo; si hay varios, lista de candidatos (institución, orden y combustible) navegable con el teclado.
- [ ] Tarjeta del vale elegido con institución, orden, combustible y **saldo actual** en grande; si el vale no es consumible (agotado, anulado o vencido) se muestra el motivo y el formulario queda deshabilitado.
- [ ] Formulario de consumo: selector de unidad (soles o galones), importe/cantidad (`CampoCantidad`), muestra la conversión y precio del vale, placa, conductor y observación (opcionales; obligatoriedad según P-06). Comprobación informativa contra el saldo con aritmética de enteros (`bigint`), sin sustituir la validación del backend.
- [ ] **Token de operación:** se genera un UUID al elegir el vale y se reutiliza en cualquier reintento tras una falla de red o un tiempo agotado (el backend devuelve el movimiento original si ya se registró). Solo se renueva después de un registro exitoso o al cambiar de vale.
- [ ] Prevención de doble envío: el botón se deshabilita mientras la petición está en curso y no admite un segundo envío.
- [ ] Mensajes por código de error: `SALDO_INSUFICIENTE` (con el saldo de `detalles`), `VALE_NO_CONSUMIBLE`, `COMBUSTIBLE_DISTINTO`, validación de cantidad, y falla de red con botón de reintento.
- [ ] Después de registrar: saldo actualizado, enlace al comprobante y formulario limpio con el foco de nuevo en el código para el siguiente despacho.
- [ ] Comprobante `/imprimir/comprobante/:movimientoId` con el encabezado de la estación, código, cantidad, saldo y fecha, e impresión del navegador.
- [ ] Campo opcional de fecha retroactiva con motivo, visible solo para el administrador (P-09).
- [ ] Acciones de administrador en el detalle del vale: anular (motivo y doble confirmación), ajustar saldo (variación con signo y motivo; `AJUSTE_NEGATIVO`) y revertir un consumo desde la línea de tiempo (motivo; `CONSUMO_YA_REVERTIDO`). Pestaña de consumos del vale con filtro de fechas.
- [ ] Botón "Procesar vencimientos" para el administrador, en el listado de vales.
- [ ] Pruebas: reutilización del token en un reintento, bloqueo del doble clic, mensajes por código, foco tras registrar, visibilidad de acciones por rol, comprobación informativa contra el saldo.

**Entregable navegable:** el despacho completo en `/despacho`.

**Verificación:**
- Despachar 30 galones de un vale de 100: el saldo pasa a 70. Intentar 80: aparece el rechazo con el saldo disponible.
- Hacer doble clic en confirmar: en la línea de tiempo del vale hay un solo movimiento.
- En las herramientas del navegador, simular falta de conexión durante el envío, volver a conectar y reintentar: queda un solo movimiento (mismo `token_operacion`).
- Mientras corre `python scripts/probar_concurrencia.py` del backend sobre otro vale, recargar la pantalla de ese vale: el saldo es coherente y nunca negativo.
- Como administrador: revertir un consumo y anular un vale con motivo; ejecutar `python -m app.cli verificar-saldos` y ver 0 diferencias.
- Leer el código de barras impreso del Bloque 7 en `/despacho` con un lector o a mano: el vale se abre directo.
- `ng test` en verde.

---

<a id="b9"></a>

### Bloque 9. Auditoría e integridad

**Objetivo:** ver quién hizo qué y detectar saldos incorrectos.
**Requiere backend:** Fase 8.
**Requerimientos:** AUD-01 a AUD-06 (AUD-01 y AUD-02 las cumple el backend; la interfaz solo las muestra).
**Rutas:** `/auditoria/bitacora`, `/auditoria/integridad`.

**Endpoints que consume:**
- `GET /auditoria/bitacora`: bitácora con filtros.
- `GET /auditoria/historial/{entidad}/{id}`: cambios de una orden, vale u otra entidad.
- `GET /auditoria/integridad/ultima`: resultado de la última verificación.
- `GET /auditoria/integridad/verificaciones`: historial de verificaciones.
- `POST /auditoria/integridad/verificar`: verificación a demanda.
- `GET /auditoria/integridad/diferencias`: diferencias con filtro de revisión.
- `POST /auditoria/integridad/diferencias/{id}/revisar`: marcar una diferencia como revisada.

Tareas:
- [ ] Bitácora (solo administrador): filtros por usuario, acción, entidad y fechas (en la URL), paginación, y detalle expandible con la comparación de valores anteriores y nuevos clave por clave. No hay acciones de editar ni borrar.
- [ ] Componente `HistorialRegistro` que consulta `GET /auditoria/historial/{entidad}/{id}`, y se integra en los detalles de orden (Bloque 6), vale (Bloque 7), institución (Bloque 5) y usuario (Bloque 3), visible para quien tenga el permiso `historial.ver`.
- [ ] Pantalla de integridad: tarjeta con la última verificación (fecha, vales revisados, diferencias), historial de verificaciones, botón "Verificar ahora" (con estado de espera) y lista de diferencias con vale, saldo almacenado y saldo recalculado; acción "Marcar como revisada" con comentario obligatorio.
- [ ] Contador de diferencias sin revisar en el menú del administrador.
- [ ] Pruebas: filtros, comparación antes y después, verificación a demanda, revisión con comentario, permisos.

**Entregable navegable:** bitácora, historial por registro e integridad de saldos con datos reales.

**Verificación:**
- Realizar una edición y un consumo; verlos en `/auditoria/bitacora` con sus valores anteriores y nuevos, y en el historial del registro.
- Siguiendo la Fase 8 del backend, alterar un saldo a mano en PostgreSQL (por ejemplo, con el *Query Tool* de pgAdmin); pulsar "Verificar ahora": aparece 1 diferencia con ambos saldos; marcarla como revisada con un comentario y comprobar que el contador baja.
- `ng test` en verde.

---

<a id="b10"></a>

### Bloque 10. Lectura OCR

**Objetivo:** subir una orden, revisar lo leído junto al original y confirmarla; una falla del OCR nunca bloquea el registro.
**Requiere backend:** Fase 11.
**Requerimientos:** OCR-01 a OCR-13.
**Rutas:** `/ocr/nueva`, `/ocr/:id/revision`, `/ocr/historial`.

**Endpoints que consume:**
- `POST /ocr/extracciones`: carga y lectura del documento (en la misma petición).
- `GET /ocr/extracciones/{id}`: estado y resultado de una extracción.
- `GET /ocr/extracciones/{id}/archivo`: documento original para el visor.
- `POST /ocr/extracciones/{id}/reintentar`: nueva lectura sin subir el archivo.
- `POST /ocr/extracciones/{id}/confirmar`: creación de la orden con los valores revisados.
- `POST /ocr/extracciones/{id}/descartar`: cancelación sin crear la orden.
- `GET /ocr/extracciones`: historial de extracciones.
- `GET /ocr/precision`: exactitud por campo según las correcciones.

Tareas:
- [ ] Pantalla `/ocr/nueva`: selección o arrastre de archivo (PDF, JPG o PNG), captura con la cámara en celular (`accept="image/*"` y `capture`), vista previa y comprobación informativa de tipo y tamaño.
- [ ] Envío con `FormData` y progreso de subida (`reportProgress`); al terminar la subida, estado "Leyendo documento…" con el `TemporizadorEspera` (segundos transcurridos). Pasados unos 15 segundos, se ofrece "Registrar manualmente".
- [ ] Resultado: extracción `lista` lleva a `/ocr/:id/revision`; extracción `fallida` lleva igualmente a la revisión en **modo manual** (campos vacíos, el archivo ya subido a la vista y el motivo de la falla), con acciones "Reintentar" y "Descartar"; errores `OCR_NO_DISPONIBLE`, `OCR_OCUPADO`, `DOCUMENTO_ILEGIBLE`, `ARCHIVO_NO_PERMITIDO` y `ARCHIVO_DEMASIADO_GRANDE` con mensajes claros.
- [ ] Pantalla de revisión en dos columnas (en una sola en pantallas pequeñas): a la izquierda el `VisorDocumento` con zoom (`GET /ocr/extracciones/{id}/archivo`), a la derecha el formulario de la orden con los valores extraídos, todos editables y reutilizando los campos del formulario de órdenes del Bloque 6.
- [ ] Confianza por campo: porcentaje y etiqueta de texto ("Revisar") además del color, según `requiere_revision`; el usuario avanza de campo en campo con el teclado.
- [ ] Institución sugerida por el RUC: se preselecciona; si no existe, un diálogo ofrece registrarla con el formulario del Bloque 5 sin perder lo capturado.
- [ ] Confirmación: el botón se habilita con los campos obligatorios completos y la marca "Datos revisados"; llama a `POST .../confirmar`; manejo de `422` junto a cada campo y de `EXTRACCION_NO_CONFIRMABLE`; al terminar, lleva al detalle de la orden creada.
- [ ] Historial `/ocr/historial` (administrador): fecha, usuario, estado, método, tiempo y confianza promedio, con filtros; tarjeta de precisión por campo (`GET /ocr/precision`) con rango de fechas.
- [ ] Atajo de teclado para confirmar (por ejemplo `Ctrl + Enter`), documentado en pantalla.
- [ ] Pruebas: subida con progreso y espera, extracción fallida en modo manual, confianza, confirmación bloqueada sin la marca de revisión, correcciones enviadas, diálogo de institución nueva.

**Entregable navegable:** el flujo completo de carga, revisión y confirmación.

**Verificación:**
- Con el servicio del backend: subir `oc_digital.pdf` (de `tests/fixtures`), revisar y confirmar; en `/ordenes` aparece la orden marcada como registrada con OCR y en `/ocr/historial` la extracción `confirmada`.
- Subir `oc_foto.jpg` y corregir un campo; confirmar y comprobar en `/ocr/historial` que la precisión refleja la corrección.
- Con `RAPIDOCR` inválido en el backend: la carga lleva a la revisión en modo manual con el mensaje de "no disponible"; confirmar la orden con datos escritos a mano.
- En un celular (misma red, a través del proxy de desarrollo o del servidor), tomar una foto con la cámara y completar el flujo.
- `ng test` en verde.

---

<a id="b11"></a>

### Bloque 11. Consultas de saldo y consumo

**Objetivo:** respuestas inmediatas a "cuánto saldo queda" y "cuánto se consumió".
**Requiere backend:** Fase 12.
**Requerimientos:** QRY-01 a QRY-08. El módulo completo es solo para Oficina y Administrador; Despachador tiene búsqueda mínima dentro de `/despacho`.
**Rutas:** buscador global (en la cabecera), `/consultas/saldo`, `/consultas/consumo`, `/consultas/estado-cuenta/:institucionId`.

**Endpoints que consume:**
- `GET /consultas/saldo/ordenes/{id}`: saldo de una orden.
- `GET /consultas/saldo/instituciones/{id}`: saldo consolidado de una institución.
- `GET /consultas/consumo`: consumo con filtros y agrupación.
- `GET /consultas/estado-cuenta/{institucion_id}`: estado de cuenta de un periodo.
- `GET /reportes/rangos`: rangos de hoy, esta semana, este mes y mes anterior en la hora de Lima.

Tareas:
- [ ] Buscador global en la cabecera, accesible desde cualquier pantalla (atajo `/`), que usa `GET /vales/buscar` (Bloque 7) con retardo, navegación con teclado y roles ARIA de lista desplegable. Con un solo resultado muestra saldo, estado e institución en un paso; con varios, la lista de candidatos.
- [ ] `/consultas/saldo`: tres modos (por vale, por orden y por institución). Por vale reutiliza `GET /vales/buscar` y `GET /vales/{id}`; por orden y por institución usan los endpoints de consulta, con presupuesto, emitido, consumido, saldo de cada vale, saldo total y presupuesto restante; los vales anulados y vencidos aparecen aparte en la consulta por institución.
- [ ] `/consultas/consumo`: filtros por institución, orden y vale (combobox), rango de fechas con los atajos de `GET /reportes/rangos`, agrupación diaria, semanal o mensual, combustible, estado y emisor; todo en la URL, con botón para limpiar; total y tabla por periodo; las reversiones ya vienen descontadas.
- [ ] `/consultas/estado-cuenta/:institucionId`: rango de fechas y tabla con saldo inicial, movimientos y saldo final; vista de impresión.
- [ ] Todas las consultas leen el backend en cada visita (sin caché en el cliente). En `/despacho`, un stream SSE autenticado con `fetch`/`ReadableStream` avisa de movimientos del vale activo y la pantalla vuelve a consultar el saldo; al reconectar también actualiza.
- [ ] Marcadores de inicio y fin de cada consulta (hooks documentados) por si se requiere medir tiempos.
- [ ] Pruebas: atajos de fecha, filtros en la URL, un solo resultado frente a varios, visualización de vales excluidos.

**Entregable navegable:** consultas de saldo y consumo con datos reales y filtros recargables.

**Verificación:**
- Buscar un código desde la cabecera y llegar al saldo en un paso; buscar un número de entidad repetido y elegir entre los candidatos.
- Con `python -m app.cli cargar-volumen --movimientos 50000`: abrir `/consultas/consumo` de una institución "este mes" agrupado por semana y comprobar en las herramientas del navegador (pestaña de red) que la respuesta tarda menos de 1 segundo; copiar la URL en otra pestaña y comprobar que muestra lo mismo.
- Registrar un consumo en `/despacho` y volver a consultar: ya refleja el nuevo saldo.
- `ng test` en verde.

---

<a id="b12"></a>

### Bloque 12. Panel, reportes y exportación

**Objetivo:** indicadores, gráficos de consumo, exportación a Excel y vistas para imprimir.
**Requiere backend:** Fase 12.
**Requerimientos:** REP-01 a REP-08. Solo Administrador y Oficina acceden a reportes y exportaciones.
**Rutas:** `/panel`, `/reportes/consumo`, `/reportes/ordenes`, `/imprimir/reporte/:tipo`.

**Endpoints que consume:**
- `GET /panel/indicadores`: indicadores del periodo actual.
- `GET /reportes/consumo/periodo`: serie agrupada por día, semana o mes.
- `GET /reportes/consumo/instituciones`: ranking por institución.
- `GET /reportes/consumo/combustibles`: distribución por combustible.
- `GET /reportes/ordenes`: órdenes y presupuesto del periodo.
- `GET /reportes/exportar/{reporte}.xlsx`: archivo Excel con los filtros aplicados.

Tareas:
- [ ] Panel de inicio: tarjetas con órdenes del mes, vales activos, galones consumidos y vales por agotarse o vencer (cada una enlaza al listado filtrado); franja de alertas; para el administrador, aviso de diferencias de saldo sin revisar con enlace a `/auditoria/integridad`.
- [ ] Componentes `GraficoBarras` y `GraficoLineas` en `shared/components/`, construidos sobre `p-chart`: opciones de `chart.js` con escala de valores "redondos" en los ejes, etiquetas formateadas con la configuración regional, `maintainAspectRatio: false` para que sea adaptable, título y descripción accesibles en el contenedor, y una tabla equivalente dentro de un `<details>` que es la representación accesible real del dato. Distinguen series por color **y** por etiqueta o patrón.
- [ ] `/reportes/consumo`: barra de filtros (rangos del Bloque 11, agrupación) y tres gráficos (por periodo, por institución y por combustible) cargados con `@defer`; todo en la URL.
- [ ] `/reportes/ordenes`: cantidad de órdenes y presupuesto total del periodo, con detalle por institución.
- [ ] Exportación a Excel: el botón descarga con `HttpClient` en modo `blob` desde `GET /reportes/exportar/{reporte}.xlsx` con los filtros activos; errores del backend mostrados como aviso.
- [ ] Vistas de impresión `/imprimir/reporte/:tipo` con el encabezado de la estación, los filtros usados, la fecha de emisión y los mismos datos que la pantalla; sin menú ni controles al imprimir (RF-REP-08).
- [ ] Pruebas: configuración de los gráficos, datos de la tabla equivalente, filtros en la URL, descarga con filtros.

**Entregable navegable:** panel, reportes con gráficos y exportación a Excel e impresión.

**Verificación:**
- Con los datos de volumen: abrir `/reportes/consumo`, cambiar de agrupación diaria a mensual y comprobar que gráficos y tabla cambian sin recargar la página.
- Exportar a Excel y abrir el archivo en Excel o LibreOffice: los totales coinciden con la tabla en pantalla.
- Imprimir o guardar como PDF `/imprimir/reporte/consumo-periodo`: se ven el encabezado de la estación, los filtros y los datos, sin menús.
- Recorrer los gráficos y comprobar que la tabla equivalente del `<details>` se lee completa con el teclado y el lector de pantalla (el `canvas` no es accesible por sí solo).
- `ng test` en verde.

---

<a id="b13"></a>

### Bloque 13. Calidad, accesibilidad y rendimiento

**Objetivo:** cerrar defectos de uso antes de la entrega.
**Requiere backend:** ninguna fase adicional.
**Requerimientos:** transversal (aplica a todos los módulos).

Tareas:
- [ ] Revisión de adaptación a 360, 768 y 1280 píxeles de ancho en los flujos críticos: despacho, revisión OCR, consultas, emisión de vales y reportes.
- [ ] Accesibilidad: teclado completo en cada pantalla, foco visible, foco al encabezado tras navegar, etiquetas en todos los campos, contraste de texto de al menos 4.5 a 1, estados con color y texto, avisos en región `aria-live`, diálogos con trampa de foco, título del documento por ruta. Auditoría con la herramienta de accesibilidad que ya traen los navegadores, sin instalar nada.
- [ ] Rendimiento: cargas diferidas por módulo, `@defer` en gráficos, `track` en todos los `@for`, listados paginados, peticiones canceladas al cambiar de pantalla; revisión del tamaño de los paquetes contra los presupuestos de `angular.json` y ajuste de los límites según lo medido.
- [ ] Revisión de calidad del código: sin `any`, sin `console.log`, sin lógica de negocio en el cliente, sin datos fijos, sin duplicación de reglas del backend.
- [ ] Mensajes y textos revisados en español claro, sin jerga técnica ni trazas visibles.
- [ ] Prueba de usabilidad con 3 usuarios reales y 4 o 5 tareas (registrar una orden con OCR, despachar un vale, consultar el saldo de un código, sacar el consumo del mes), con observaciones anotadas y corregidas.
- [ ] Completar las pruebas de componentes de los flujos críticos y comprobar que `ng test` pasa completo.
- [ ] `node scripts/verificar-dependencias.mjs` sin cambios.

**Entregable navegable:** aplicación completa y estable sobre datos de volumen.

**Verificación:**
- `ng test` y `ng build` en verde, sin advertencias de presupuesto nuevas.
- Recorrer en celular y en escritorio los cuatro flujos de la prueba de usabilidad sin errores ni mensajes en la consola del navegador.
- La auditoría de accesibilidad del navegador no reporta errores críticos en las pantallas principales.

---

<a id="b14"></a>

### Bloque 14. Compilación, integración y entrega

**Objetivo:** la aplicación compilada, servida por el backend desde un solo origen y lista para el uso real.
**Requiere backend:** Fases 13 y 14.
**Requerimientos:** transversal (integración de todos los módulos).

Tareas:
- [ ] `ng build` de producción y revisión de la carpeta de salida (`dist/.../browser`); configurar `FRONTEND_DIST` del backend para que apunte a ella.
- [ ] Confirmar `base href="/"` y que las rutas internas funcionan al recargar (el backend devuelve `index.html`).
- [ ] Confirmar las cabeceras de caché: archivos con hash en el nombre con caché larga e `index.html` sin caché.
- [ ] Confirmar que no hay `service worker` registrado (`navigator.serviceWorker.getRegistrations()` vacío) ni manifiesto: sin PWA.
- [ ] Revisar la consola del navegador con la política de seguridad de contenido del backend; si aparecen violaciones, ajustar la política en el backend.
- [ ] Manual de usuario breve, con capturas, de una o dos páginas por flujo (registro con OCR, despacho, consultas, reportes).
- [ ] Capacitación a los 7 usuarios con práctica sobre datos de prueba y un periodo corto de adaptación antes del uso real.
- [ ] Congelar la interfaz durante el estudio: solo correcciones críticas, con fecha, y etiqueta de git (`estudio-v1.0`).
- [ ] Guion maestro de verificación en `docs/guiones/` con los recorridos de cada bloque.

**Entregable navegable:** la aplicación completa en `http://127.0.0.1:8000` (o el dominio de producción), con la API en el mismo origen.

**Verificación:**
- `ng build` en la raíz del repositorio y `fastapi run` en `backend/`: abrir `http://127.0.0.1:8000`, iniciar sesión, recargar `/ordenes` y `/vales/{id}`: cargan la aplicación; `GET /api/v1/ruta-inexistente` devuelve JSON `404`, no la aplicación.
- En las herramientas del navegador (pestaña de red): `index.html` sin caché y los archivos con hash con caché larga; ningún `service worker`.
- `python scripts/smoke.py --hasta 13` del backend en verde con la aplicación servida.
- Un usuario nuevo completa los cuatro flujos con el manual y sin ayuda.

[↑ Volver al índice](#indice)

---

<a id="s7"></a>

## 7. Decisiones pendientes

**Cerradas en la versión 3.2:**
- [x] **Capa de interfaz:** PrimeNG 21 + `@primeuix/themes` + `primeicons` para componentes, `iconify-icon` para la iconografía propia, Tailwind 4 para la maquetación y `chart.js` mediante `p-chart` para los gráficos. Sustituye la decisión anterior de construir tabla, diálogo, combos y gráficos a mano.
- [x] **Ubicación del código:** el proyecto Angular vive en la **raíz del repositorio**, junto a `backend/`. No existe ni se creará una carpeta `frontend/`.
- [x] **Convención de nombres:** estructura de carpetas en inglés (`core/`, `shared/`, `features/`, `layouts/`) y nombres de dominio en español, con los controles de formulario idénticos a los campos de la API.

**Pendientes:**
- [ ] **Versión de Node.js** que exija Angular 21.2.0 al crear el proyecto (se confirma con `ng version`). *Afecta:* Bloque 0.
- [ ] **PDF por impresión del navegador** (supuesto, igual que T-02 del backend): si se exige un PDF generado en el servidor, hay que sumar una librería. *Afecta:* Bloques 7, 8, 11 y 12.
- [ ] **Código de barras Code 128 propio** (supuesto, igual que T-03 del backend): si se prefiere QR, hay que sumar una librería o escribir un generador. *Afecta:* Bloque 7.
- [ ] **Pruebas de navegador automatizadas:** el plan no las incluye porque exigen herramientas nuevas (Playwright o similares). Si se permiten, se agregan en el Bloque 13. *Afecta:* Bloque 13.
- [ ] **Medición de cobertura de pruebas y análisis de estilo:** requieren paquetes que `ng new` no trae (proveedor de cobertura de Vitest, ESLint, Prettier). Si se permiten, se agregan al Bloque 1. *Afecta:* Bloques 1 y 13.
- [ ] **Brechas del backend G1 a G5** (sección 4.4): hay que aceptarlas o ajustarlas antes de iniciar los bloques que las usan.
- [ ] **Puntos por confirmar de negocio** (P-01 a P-13 de la especificación): cada bloque usa el supuesto por defecto indicado en el plan de backend mientras tanto.

[↑ Volver al índice](#indice)

---

<a id="s8"></a>

## 8. Cobertura de requerimientos y endpoints

Se verificó automáticamente:
- **Requerimientos:** La trazabilidad se recalculará con el plan de backend actualizado; las cifras heredadas no aplican.
- **Endpoints:** los endpoints del catálogo de `plan-implementacion-backend-fastapi.md` están asignados a un bloque, cada uno exactamente a uno (0 sin consumir, 0 inexistentes en el backend).

Endpoints por bloque: Bloque 0: 1; Bloque 1: 1; Bloque 2: 6; Bloque 3: 7; Bloque 4: 12; Bloque 5: 7; Bloque 6: 11; Bloque 7: 9; Bloque 8: 7; Bloque 9: 7; Bloque 10: 8; Bloque 11: 5; Bloque 12: 6.

Requerimientos que el frontend no resuelve con una pantalla propia (los cumple el backend o se muestran en otra pantalla):
- **AUD-01** y **AUD-02**: el backend registra las acciones y garantiza la inalterabilidad; la bitácora y el historial (Bloque 9) solo los muestran.
- **VAL-14**: la interfaz no ofrece ninguna acción para eliminar vales ni movimientos.

[↑ Volver al índice](#indice)

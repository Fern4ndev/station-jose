# Frontend (Angular 21)

## Comandos
- Servidor: ng serve
- Pruebas: ng test
- Build: ng build

## Arquitectura
- Componentes standalone, sin NgModules nuevos.
- Estado local con signals; control flow moderno (@if, @for) en templates.
- Llamadas HTTP solo en servicios (inyectados con inject()), nunca en componentes.
- Interceptor HTTP para el token; guards para rutas protegidas.
- Rutas con carga diferida (lazy loading) por funcionalidad.

## Convenciones
- TypeScript estricto, sin any.
- Interfaces para los modelos que devuelve la API.
- URL de la API en los archivos de environment, no escrita en el código.
- Formularios reactivos con validación.
- Nada de lógica de negocio en los templates.

## Pruebas
- Probar servicios (con HttpTestingController) y componentes clave.
- Primero la prueba, luego la implementación.
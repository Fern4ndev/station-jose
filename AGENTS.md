# Proyecto: [Station]

## Estructura
- backend/  → Laravel (API REST, MySQL, Sanctum)
- frontend/ → Angular 21 (standalone components, signals)

## Reglas
- No mezclar código entre backend y frontend.
- Backend: controladores delgados, lógica en Services, validación con Form Requests, API Resources para JSON.
- Cambios de base de datos solo con migraciones.
- Frontend: servicios para HTTP, interceptor para el token, nada de lógica de negocio en templates.
- TDD: primero la prueba que falla.
- Nunca commitear .env ni claves.
# Componentes compartidos

La biblioteca UI del sistema es **PrimeNG 21** (`primeng@^21.1.10`). El tema Aura
se configura en `src/app/app.config.ts` y los estilos globales declaran las capas
de PrimeNG en `src/styles.css`.

Los componentes de esta carpeta son wrappers de dominio ligeros alrededor de
PrimeNG o componentes compartidos propios. Deben ser standalone, usar señales de
entrada/salida y `OnPush`, mantener nombres de archivos basados en el nombre de
su componente/carpeta, y crear una hoja CSS local solo si Tailwind y el tema no
cubren un requisito visual concreto. Evitar archivos de prueba vacíos; agregar
specs cuando se solicite cobertura o la lógica tenga comportamiento no trivial.

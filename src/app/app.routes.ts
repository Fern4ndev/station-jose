import { Routes } from '@angular/router';
import { authGuard, guestGuard, permissionGuard } from './core/guards/auth.guards';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'auth/login',
  },
  {
    path: 'auth/login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login-page/login-page').then((module) => module.LoginPage),
  },
  {
    path: 'access-denied',
    loadComponent: () => import('./features/system/access-denied').then((module) => module.AccessDeniedPage),
  },
  {
    path: 'not-found',
    loadComponent: () => import('./features/system/not-found').then((module) => module.NotFoundPage),
  },
  {
    path: 'app',
    canActivate: [authGuard],
    canActivateChild: [authGuard],
    loadComponent: () => import('./layouts/admin/admin').then((module) => module.AdminLayout),
    children: [
      {
        path: '',
        loadComponent: () => import('./features/auth/home-redirect').then((module) => module.AppHomeRedirect),
      },
      {
        path: 'dashboard',
        canActivate: [permissionGuard],
        data: { permission: 'reports.read', title: 'Panel principal', description: 'Resumen operativo del sistema.' },
        loadComponent: () => import('./features/dashboard/dashboard-page').then((module) => module.DashboardPage),
      },
      {
        path: 'attendant/workspace',
        canActivate: [permissionGuard],
        data: { permission: 'attendances.create', title: 'Espacio de atención', description: 'Consulta de órdenes y registro de atenciones.' },
        loadComponent: () => import('./features/attendant/workspace-page').then((module) => module.WorkspacePage),
      },
      {
        path: 'users',
        canActivate: [permissionGuard],
        data: { permission: 'users.read', title: 'Usuarios', description: 'Administración de cuentas y roles predefinidos.', listDescription: 'Cuentas de usuario autorizadas para este perfil.', columns: ['Usuario', 'Rol', 'Sede', 'Estado'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
      {
        path: 'purchase-orders',
        canActivate: [permissionGuard],
        data: { permission: 'purchase_orders.read', title: 'Órdenes de compra', description: 'Consulta autorizaciones y saldo disponible por combustible.', listDescription: 'Cantidades autorizadas, despachadas y disponibles por combustible.', columns: ['Orden / entidad', 'Sede', 'Fecha', 'Combustible', 'Autorizado', 'Despachado', 'Disponible', 'Estado'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
      {
        path: 'attendances/pending-verification',
        canActivate: [permissionGuard],
        data: { permission: 'attendances.verify', title: 'Verificación', description: 'Revisión administrativa de vales físicos por atención.', listDescription: 'Una fila por atención pendiente u observada.', columns: ['Vale / orden', 'Combustible', 'Galones', 'Fecha y hora', 'Usuario', 'Estado'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
      {
        path: 'attendances',
        canActivate: [permissionGuard],
        data: { permission: 'attendances.create', title: 'Atenciones', description: 'Registro y consulta de atenciones de combustible.', listDescription: 'Historial de despachos visibles para tu perfil.', columns: ['Vale / orden', 'Grifero', 'Sede', 'Despachado', 'Verificación'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
      {
        path: 'vouchers',
        canActivate: [permissionGuard],
        data: { permission: 'vouchers.read', title: 'Vales', description: 'Consulta de vales, saldos y su historial de atenciones.', listDescription: 'Autorización del documento y saldo del vale por combustible.', columns: ['N.º de vale', 'Orden / emisor', 'Combustible', 'Atendido', 'Saldo del vale', 'Verificación'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
      {
        path: 'reports/attendances',
        canActivate: [permissionGuard],
        data: { permission: 'reports.read', title: 'Reportes', description: 'Reportes operativos de órdenes y atenciones.', listDescription: 'Órdenes, vales y atenciones según filtros y permisos.', columns: ['Reporte', 'Período', 'Estado', 'Acción'] },
        loadComponent: () => import('./shared/components/feature-placeholder/feature-placeholder').then((module) => module.FeaturePlaceholder),
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'not-found',
  },
];

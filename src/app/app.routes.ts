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
    loadComponent: () => import('./features/auth/login-page').then((module) => module.LoginPage),
  },
  {
    path: 'access-denied',
    loadComponent: () => import('./pages/access-denied').then((module) => module.AccessDeniedPage),
  },
  {
    path: 'not-found',
    loadComponent: () => import('./pages/not-found').then((module) => module.NotFoundPage),
  },
  {
    path: 'app',
    canActivate: [authGuard],
    canActivateChild: [authGuard],
    loadComponent: () => import('./layouts/app-shell').then((module) => module.AppShell),
    children: [
      {
        path: '',
        loadComponent: () => import('./pages/app-home-redirect').then((module) => module.AppHomeRedirect),
      },
      {
        path: 'dashboard',
        canActivate: [permissionGuard],
        data: { permission: 'reports.read', title: 'Panel principal', description: 'Resumen operativo del sistema.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'attendant/workspace',
        canActivate: [permissionGuard],
        data: { permission: 'attendances.create', title: 'Espacio de atención', description: 'Consulta de órdenes y registro de atenciones.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'users',
        canActivate: [permissionGuard],
        data: { permission: 'users.manage', title: 'Usuarios', description: 'Administración de cuentas y permisos.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'orders',
        canActivate: [permissionGuard],
        data: { permission: 'purchase_orders.read', title: 'Órdenes de compra', description: 'Consulta y gestión de órdenes de compra.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'attendances',
        canActivate: [permissionGuard],
        data: { permission: 'attendances.create', title: 'Atenciones', description: 'Registro y consulta de atenciones de combustible.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'vouchers',
        canActivate: [permissionGuard],
        data: { permission: 'vouchers.read', title: 'Vales', description: 'Consulta de vales, saldos y su historial de atenciones.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'verifications',
        canActivate: [permissionGuard],
        data: { permission: 'vouchers.verify', title: 'Verificación', description: 'Revisión administrativa de vales físicos.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
      {
        path: 'reports',
        canActivate: [permissionGuard],
        data: { permission: 'reports.read', title: 'Reportes', description: 'Reportes operativos de órdenes y atenciones.' },
        loadComponent: () => import('./pages/feature-page').then((module) => module.FeaturePage),
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'not-found',
  },
];

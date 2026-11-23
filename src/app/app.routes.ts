import { Routes } from '@angular/router';
import { authGuard, loginGuard, navGuard } from './core/guards/auth-guard';
import { Auth } from './layouts/auth/auth';

export const routes: Routes = [
  {
    path: 'login',
    component: Auth,
    canActivate: [loginGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./features/auth/login').then((m) => m.Login),
      },
    ],
  },
  {
    path: '',
    loadComponent: () => import('./layouts/admin/admin').then((m) => m.Admin),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        canActivate: [navGuard('/')],
        loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'ordenes',
        canActivate: [navGuard('/ordenes')],
        loadComponent: () => import('./features/orders/orders').then((m) => m.Orders),
      },
      {
        path: 'vales',
        canActivate: [navGuard('/vales')],
        loadComponent: () => import('./features/vouchers/vouchers').then((m) => m.Vouchers),
      },
      {
        path: 'atenciones',
        canActivate: [navGuard('/atenciones')],
        loadComponent: () =>
          import('./features/attendances/attendances').then((m) => m.Attendances),
      },
      {
        path: 'reportes',
        canActivate: [navGuard('/reportes')],
        loadComponent: () => import('./features/reports/reports').then((m) => m.Reports),
      },
      {
        path: 'usuarios',
        canActivate: [navGuard('/usuarios')],
        loadComponent: () => import('./features/users/users').then((m) => m.Users),
      },
      {
        path: '**',
        loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
      },
    ],
  },
];

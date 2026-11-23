import { Routes } from '@angular/router';
import { authGuard, loginGuard, navGuard } from './core/guards/auth-guard';
import { AuthLayout } from './layouts/auth/auth-layout';

export const routes: Routes = [
  {
    path: 'login',
    component: AuthLayout,
    canActivate: [loginGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./layouts/auth/login-page').then((m) => m.LoginPage),
      },
    ],
  },
  {
    path: '',
    loadComponent: () => import('./layouts/admin/admin-layout').then((m) => m.AdminLayout),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        canActivate: [navGuard('/')],
        loadComponent: () =>
          import('./features/dashboard/dashboard-page').then((m) => m.DashboardPage),
      },
      {
        path: 'ordenes',
        canActivate: [navGuard('/ordenes')],
        loadComponent: () => import('./features/orders/orders-page').then((m) => m.OrdersPage),
      },
      {
        path: 'vales',
        canActivate: [navGuard('/vales')],
        loadComponent: () => import('./features/vouchers/vouchers-page').then((m) => m.VouchersPage),
      },
      {
        path: 'atenciones',
        canActivate: [navGuard('/atenciones')],
        loadComponent: () =>
          import('./features/attendances/attendances-page').then((m) => m.AttendancesPage),
      },
      {
        path: 'reportes',
        canActivate: [navGuard('/reportes')],
        loadComponent: () => import('./features/reports/reports-page').then((m) => m.ReportsPage),
      },
      {
        path: 'usuarios',
        canActivate: [navGuard('/usuarios')],
        loadComponent: () => import('./features/users/users-page').then((m) => m.UsersPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];

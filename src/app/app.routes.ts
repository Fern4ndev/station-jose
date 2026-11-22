import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';
import { adminOnlyGuard } from './core/guards/permission.guard';
import { AuthLayout } from './layouts/auth/auth-layout';

export const routes: Routes = [
  {
    path: 'login',
    component: AuthLayout,
    canActivate: [guestGuard],
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
        loadComponent: () =>
          import('./features/dashboard/dashboard-page').then((m) => m.DashboardPage),
      },
      {
        path: 'ordenes',
        loadComponent: () => import('./features/orders/orders-page').then((m) => m.OrdersPage),
      },
      {
        path: 'vales',
        loadComponent: () => import('./features/vouchers/vouchers-page').then((m) => m.VouchersPage),
      },
      {
        path: 'atenciones',
        loadComponent: () =>
          import('./features/attendances/attendances-page').then((m) => m.AttendancesPage),
      },
      {
        path: 'reportes',
        loadComponent: () => import('./features/reports/reports-page').then((m) => m.ReportsPage),
      },
      {
        path: 'usuarios',
        canActivate: [adminOnlyGuard],
        loadComponent: () => import('./features/users/users-page').then((m) => m.UsersPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];

import { Routes } from '@angular/router';
import { adminOnlyGuard } from './features/users/users-access';
import { AdminLayout } from './layouts/admin/admin-layout';
import { AuthLayout } from './layouts/auth/auth-layout';
import { LoginPage } from './layouts/auth/login-page';

export const routes: Routes = [
  {
    path: 'login',
    component: AuthLayout,
    children: [{ path: '', component: LoginPage }],
  },
  {
    path: '',
    component: AdminLayout,
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

import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '../../../../core/services/auth/auth';
import { ROLE_LABELS } from '../../../../core/models/auth.models';

interface NavigationItem {
  readonly label: string;
  readonly path: string;
  readonly permission: string;
}

const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { label: 'Panel principal', path: '/app/dashboard', permission: 'reports.read' },
  { label: 'Órdenes de compra', path: '/app/purchase-orders', permission: 'purchase_orders.read' },
  { label: 'Vales', path: '/app/vouchers', permission: 'vouchers.read' },
  { label: 'Atenciones', path: '/app/attendances', permission: 'attendances.create' },
  { label: 'Mis atenciones', path: '/app/attendant/attendances', permission: 'attendances.read_own' },
  { label: 'Saldos', path: '/app/balances', permission: 'balances.read' },
  { label: 'Verificación', path: '/app/attendances/pending-verification', permission: 'vouchers.verify' },
  { label: 'Reportes', path: '/app/reports', permission: 'reports.read' },
  { label: 'Usuarios', path: '/app/users', permission: 'users.manage' },
];

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive],
  selector: 'app-sidebar',
  styleUrl: './sidebar.css',
  templateUrl: './sidebar.html',
})
export class Sidebar {
  private readonly auth = inject(AuthStore);

  readonly open = input(false);
  readonly closeMenu = output<void>();

  protected readonly user = this.auth.user;
  protected readonly navigation = computed(() => {
    const role = this.user()?.role;
    return NAVIGATION_ITEMS.filter((item) => this.auth.hasPermission(item.permission)).map((item) =>
      item.permission === 'attendances.create' && role === 'ATTENDANT'
        ? { ...item, label: 'Espacio de atención', path: '/app/attendant/workspace' }
        : item,
    );
  });
  protected readonly roleLabel = computed(() => {
    const role = this.user()?.role;
    return role ? ROLE_LABELS[role] : '';
  });
  protected readonly branchName = computed(() => this.user()?.branch?.name ?? 'Sede no asignada');

  protected onNavigate(): void {
    this.closeMenu.emit();
  }
}

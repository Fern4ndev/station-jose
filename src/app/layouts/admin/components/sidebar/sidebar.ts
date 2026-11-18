import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '../../../../core/services/auth/auth';
import { ROLE_LABELS } from '../../../../core/models/auth.models';
import { NAVIGATION } from '../../../../core/constants/navigation';
import { PopoverModule } from 'primeng/popover';
import { ProfileAvatar } from '../../../../shared/components/avatar/avatar';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, PopoverModule, ProfileAvatar],
  selector: 'app-sidebar',
  styleUrl: './sidebar.css',
  templateUrl: './sidebar.html',
})
export class Sidebar {
  private readonly auth = inject(AuthStore);
  private readonly destroyRef = inject(DestroyRef);
  private readonly mobileQuery = window.matchMedia('(max-width: 760px)');

  readonly open = input(false);
  readonly closeMenu = output<void>();
  readonly logoutClick = output<void>();
  protected readonly isMobile = signal(this.mobileQuery.matches);

  constructor() {
    const onChange = (event: MediaQueryListEvent): void => this.isMobile.set(event.matches);
    this.mobileQuery.addEventListener('change', onChange);
    this.destroyRef.onDestroy(() => this.mobileQuery.removeEventListener('change', onChange));
  }

  protected readonly user = this.auth.user;
  protected readonly navigation = computed(() => NAVIGATION.flatMap((group) => group.items)
    .filter((item) => this.auth.hasPermission(item.permission)));
  protected readonly icons: Readonly<Record<string, string>> = {
    '/dashboard': 'dashboard', '/purchase-orders': 'description', '/vouchers': 'confirmation_number',
    '/attendant/workspace': 'local_gas_station', '/attendant/attendances': 'history',
    '/attendances': 'receipt_long', '/balances': 'account_balance_wallet',
    '/reports': 'bar_chart', '/users': 'group',
  };
  protected readonly roleLabel = computed(() => {
    const role = this.user()?.role;
    return role ? ROLE_LABELS[role] : '';
  });
  protected readonly branchLabel = computed(() => this.user()?.role === 'ATTENDANT' ? 'Sede asignada' : 'Cobertura');
  protected readonly branchName = computed(() => {
    const user = this.user();
    return user?.role === 'ATTENDANT' ? user.branch?.name ?? 'Sede no asignada' : 'Todas las sedes';
  });

  protected onNavigate(): void {
    this.closeMenu.emit();
  }
}

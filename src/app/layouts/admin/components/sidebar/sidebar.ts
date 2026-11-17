import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '../../../../core/services/auth/auth';
import { ROLE_LABELS } from '../../../../core/models/auth.models';
import { NAVIGATION } from '../../../../core/constants/navigation';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive],
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
  protected readonly isMobile = signal(this.mobileQuery.matches);

  constructor() {
    const onChange = (event: MediaQueryListEvent): void => this.isMobile.set(event.matches);
    this.mobileQuery.addEventListener('change', onChange);
    this.destroyRef.onDestroy(() => this.mobileQuery.removeEventListener('change', onChange));
  }

  protected readonly user = this.auth.user;
  protected readonly navigation = computed(() => NAVIGATION
    .map((group) => ({ ...group, items: group.items.filter((item) => this.auth.hasPermission(item.permission)) }))
    .filter((group) => group.items.length > 0));
  protected readonly roleLabel = computed(() => {
    const role = this.user()?.role;
    return role ? ROLE_LABELS[role] : '';
  });
  protected readonly branchName = computed(() => this.user()?.branch?.name ?? 'Sede no asignada');

  protected onNavigate(): void {
    this.closeMenu.emit();
  }
}

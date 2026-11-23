import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, startWith } from 'rxjs';
import { ROLE_HOME, navChildForRoute, type NavChild } from '../../core/constants/nav';
import { AdminUiState } from './admin-ui-state';
import { AdminHeader } from './components/header/admin-header';
import { AdminSidebar } from './components/sidebar/admin-sidebar';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AdminHeader, AdminSidebar, RouterOutlet],
  selector: 'app-admin-layout',
  templateUrl: './admin-layout.html',
})
export class AdminLayout {
  private readonly router = inject(Router);
  protected readonly state = inject(AdminUiState);

  protected readonly menuOpen = signal(false);

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((event) => event instanceof NavigationEnd),
      map(() => this.router.url),
      startWith(this.router.url),
    ),
    { initialValue: '/' },
  );

  private readonly currentNav = computed(() => navChildForRoute(this.url()));
  protected readonly page = computed(() => this.currentNav()?.id ?? 'dashboard');
  protected readonly pageLabel = computed(() => this.currentNav()?.label ?? 'Panel de control');

  constructor() {
    effect(() => {
      const current = this.currentNav();
      const allowed =
        current !== undefined && this.state.navItems().some((item) => item.id === current.id);
      if (!allowed) {
        const role = this.state.role();
        void this.router.navigateByUrl(role ? ROLE_HOME[role] : '/');
      }
    });
  }

  protected onPageChange(page: NavChild): void {
    this.menuOpen.set(false);
    void this.router.navigateByUrl(page.path);
  }

  protected toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  protected closeMenu(): void {
    this.menuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.closeMenu();
  }
}

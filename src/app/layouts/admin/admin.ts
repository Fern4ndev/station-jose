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
import { ROLE_HOME, navChildForRoute } from '../../core/constants/nav';
import { AuthService } from '../../core/services/auth/auth';
import { Header } from './components/header/header';
import { Sidebar } from './components/sidebar/sidebar';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Header, Sidebar, RouterOutlet],
  selector: 'app-admin',
  templateUrl: './admin.html',
})
export class Admin {
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  /** Escritorio: riel de iconos (76 px) frente a la barra completa (252 px). */
  protected readonly sidebarCollapsed = signal(false);
  /** Móvil: cajón superpuesto con fondo atenuado. */
  protected readonly mobileMenuOpen = signal(false);

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((event) => event instanceof NavigationEnd),
      map(() => this.router.url),
      startWith(this.router.url),
    ),
    { initialValue: '/' },
  );

  private readonly currentNav = computed(() => navChildForRoute(this.url()));
  protected readonly pageLabel = computed(() => this.currentNav()?.label ?? 'Panel de control');

  constructor() {
    // Un rol sin acceso a la sección abierta vuelve a su portada.
    effect(() => {
      const current = this.currentNav();
      const role = this.auth.role();
      if (current && role && !current.roles.includes(role)) {
        void this.router.navigateByUrl(ROLE_HOME[role]);
      }
    });
  }

  protected toggleSidebar(): void {
    this.sidebarCollapsed.update((collapsed) => !collapsed);
  }

  protected toggleMobileMenu(): void {
    this.mobileMenuOpen.update((open) => !open);
  }

  protected closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.closeMobileMenu();
  }
}

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
import { PAGE_LABELS, PAGE_PATHS, pageFromUrl, type PageId } from './admin-nav';
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

  protected readonly page = computed(() => pageFromUrl(this.url()));
  protected readonly pageLabel = computed(() => PAGE_LABELS[this.page()]);

  constructor() {
    effect(() => {
      const allowed = this.state.navItems().some((item) => item.id === this.page());
      if (!allowed) {
        void this.router.navigateByUrl('/');
      }
    });
  }

  protected onPageChange(page: PageId): void {
    this.menuOpen.set(false);
    void this.router.navigateByUrl(`/${PAGE_PATHS[page]}`);
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

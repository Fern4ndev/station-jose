import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { catchError, finalize, of } from 'rxjs';
import { AuthSessionService, AuthStore } from '../../core/services/auth/auth';
import { Header } from './components/header/header';
import { Sidebar } from './components/sidebar/sidebar';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Header, Sidebar, RouterOutlet],
  selector: 'app-admin-layout',
  styleUrl: './admin.css',
  templateUrl: './admin.html',
})
export class AdminLayout {
  private readonly auth = inject(AuthStore);
  private readonly session = inject(AuthSessionService);
  private readonly router = inject(Router);
  protected readonly menuOpen = signal(false);

  protected openMenu(): void {
    this.menuOpen.set(true);
  }

  protected closeMenu(): void {
    this.menuOpen.set(false);
  }

  protected logout(): void {
    this.session.logout().pipe(
      catchError(() => of(void 0)),
      finalize(() => {
        this.auth.clearSession();
        void this.router.navigate(['/auth/login']);
      }),
    ).subscribe();
  }
}

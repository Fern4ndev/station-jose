import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { finalize, of, catchError } from 'rxjs';
import { ROLE_LABELS } from '../core/models/auth.models';
import { AuthSessionService, AuthStore } from '../core/services/auth/auth';
import { APP_NAVIGATION } from './app-navigation';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  selector: 'app-shell',
  styleUrl: './app-shell.css',
  templateUrl: './app-shell.html',
})
export class AppShell {
  private readonly auth = inject(AuthSessionService);
  private readonly authStore = inject(AuthStore);
  private readonly router = inject(Router);

  protected readonly user = this.authStore.user;
  protected readonly roleLabel = computed(() => {
    const role = this.user()?.role;
    return role ? ROLE_LABELS[role] : '';
  });
  protected readonly userName = computed(() => {
    const user = this.user();
    return user ? `${user.firstName} ${user.lastName}` : '';
  });
  protected readonly branchName = computed(() => this.user()?.branch?.name ?? 'Sin sede asignada');
  protected readonly initials = computed(() => {
    const user = this.user();
    return user ? `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase() : 'SJ';
  });
  protected readonly navigation = computed(() =>
    APP_NAVIGATION.filter((item) => this.authStore.hasPermission(item.permission)),
  );
  protected readonly isMobileNavigationOpen = signal(false);
  protected readonly isSigningOut = signal(false);

  protected toggleMobileNavigation(): void {
    this.isMobileNavigationOpen.update((open) => !open);
  }

  protected closeMobileNavigation(): void {
    this.isMobileNavigationOpen.set(false);
  }

  protected signOut(): void {
    if (this.isSigningOut()) {
      return;
    }

    this.isSigningOut.set(true);
    let serverRevocationFailed = false;

    this.auth
      .logout()
      .pipe(
        catchError(() => {
          serverRevocationFailed = true;
          return of(undefined);
        }),
        finalize(() => {
          this.authStore.clearSession();
          void this.router.navigate(['/auth/login'], {
            queryParams: { signedOut: serverRevocationFailed ? 'local' : 'true' },
          });
        }),
      )
      .subscribe();
  }
}

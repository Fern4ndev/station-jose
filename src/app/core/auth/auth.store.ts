import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthSession, LoginResult } from './auth.models';

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private readonly router = inject(Router);
  private readonly sessionState = signal<AuthSession | null>(null);
  private expiryTimer: ReturnType<typeof setTimeout> | undefined;

  readonly session = this.sessionState.asReadonly();
  readonly user = computed(() => this.sessionState()?.user ?? null);
  readonly permissions = computed(() => this.sessionState()?.permissions ?? []);
  readonly accessToken = computed(() => this.sessionState()?.accessToken ?? null);
  readonly isAuthenticated = computed(() => this.sessionState() !== null);

  setSession(response: LoginResult): void {
    this.clearExpiryTimer();

    const expiresInSeconds = Math.max(0, response.expiresIn);
    const expiresAt = Date.now() + expiresInSeconds * 1_000;

    this.sessionState.set({
      accessToken: response.accessToken,
      expiresAt,
      user: response.user,
      permissions: [...response.permissions],
    });

    this.expiryTimer = setTimeout(() => {
      this.clearSession();
      void this.router.navigate(['/auth/login'], { queryParams: { expired: 'true' } });
    }, expiresInSeconds * 1_000);
  }

  clearSession(): void {
    this.clearExpiryTimer();
    this.sessionState.set(null);
  }

  hasPermission(permission: string): boolean {
    return this.permissions().includes(permission);
  }

  private clearExpiryTimer(): void {
    if (this.expiryTimer !== undefined) {
      clearTimeout(this.expiryTimer);
      this.expiryTimer = undefined;
    }
  }
}

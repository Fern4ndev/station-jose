import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, map, of, tap, type Observable } from 'rxjs';
import { AuthApiService } from '../api/auth-api.service';
import { APP_ROUTES, SESSION_EXPIRED_REASON } from '../constants/system.constants';
import type {
  CurrentUserResponse,
  LoginCredentials,
  Permission,
  UserRole,
} from '../models/auth.model';
import { TokenStorageService } from './token-storage.service';

/**
 * Estado de sesión de la aplicación.
 * Los signals se derivan del almacenamiento, de modo que la sesión restaurada al
 * recargar ya está disponible de forma síncrona para guards y plantillas.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(AuthApiService);
  private readonly storage = inject(TokenStorageService);
  private readonly router = inject(Router);

  private readonly authenticatingState = signal(false);
  private readonly verifiedState = signal(false);

  readonly token = this.storage.token;
  readonly user = this.storage.user;
  readonly permissions = this.storage.permissions;
  readonly authenticating = this.authenticatingState.asReadonly();
  readonly isVerified = this.verifiedState.asReadonly();

  readonly isAuthenticated = computed(
    () => this.storage.token() !== null && this.storage.user() !== null,
  );
  readonly role = computed<UserRole | null>(() => this.storage.user()?.role ?? null);
  readonly fullName = computed(() => {
    const user = this.storage.user();
    return user ? `${user.first_name} ${user.last_name}` : '';
  });
  readonly initials = computed(() =>
    this.fullName()
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase(),
  );
  readonly branchName = computed(() => this.storage.user()?.branch?.name ?? 'Todas las sedes');

  /** Autentica contra `POST /auth/login` y persiste el JWT. */
  login(credentials: LoginCredentials): Observable<CurrentUserResponse> {
    this.authenticatingState.set(true);
    return this.api
      .login({ email: credentials.email.trim(), password: credentials.password })
      .pipe(
        tap((response) => {
          this.storage.save(response, credentials.remember);
          this.verifiedState.set(true);
        }),
        map((response): CurrentUserResponse => ({
          ...response.user,
          permissions: response.permissions,
        })),
        finalize(() => this.authenticatingState.set(false)),
      );
  }

  /**
   * Revoca la sesión en el backend (best-effort) y limpia el estado local.
   * La navegación al login es inmediata: no se espera la respuesta del servidor.
   */
  logout(redirectToLogin = true): void {
    if (this.storage.token()) {
      this.api
        .logout()
        .pipe(catchError(() => of(undefined)))
        .subscribe({ error: () => undefined });
    }
    this.clearSession();
    if (redirectToLogin) {
      void this.router.navigate([APP_ROUTES.login]);
    }
  }

  /**
   * Valida el token guardado contra `GET /auth/me`.
   * Cachea el resultado por sesión para no repetir la llamada en cada guard.
   */
  checkAuthStatus(force = false): Observable<boolean> {
    if (!this.storage.token()) {
      this.verifiedState.set(false);
      return of(false);
    }
    if (this.verifiedState() && !force) {
      return of(true);
    }
    return this.api.me().pipe(
      tap((user) => {
        this.storage.updateUser(user);
        this.verifiedState.set(true);
      }),
      map(() => true),
      catchError(() => {
        this.clearSession();
        return of(false);
      }),
    );
  }

  hasPermission(permission: Permission): boolean {
    return this.storage.permissions().includes(permission);
  }

  clearSession(): void {
    this.storage.clear();
    this.verifiedState.set(false);
  }

  /** Usado por `errorInterceptor` ante un 401 de una sesión ya iniciada. */
  expireSession(): void {
    const hadSession = this.isAuthenticated();
    this.clearSession();
    if (hadSession) {
      void this.router.navigate([APP_ROUTES.login], {
        queryParams: { reason: SESSION_EXPIRED_REASON },
      });
    }
  }
}

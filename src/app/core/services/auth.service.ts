import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, map, of, tap, throwError, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import {
  LOCKOUT_MS,
  RATE_LIMIT_MAX,
  RATE_LIMIT_WINDOW_MS,
} from '../constants/auth-rate-limit';
import { APP_ROUTES, ROLE_HOME, SESSION_EXPIRED_REASON } from '../constants/nav';
import { isApiError } from '../models/error.model';
import type {
  CurrentUserResponse,
  LoginCredentials,
  LoginRequest,
  Permission,
  TokenResponse,
  UserRole,
} from '../models/auth.model';
import { TokenStorageService } from './token-storage.service';

/**
 * Estado de sesión de la aplicación y endpoints de autenticación.
 * Los signals se derivan del almacenamiento, de modo que la sesión restaurada al
 * recargar ya está disponible de forma síncrona para guards y plantillas.
 */
@Injectable({ providedIn: 'root' })
export class AuthService extends BaseApi {
  private readonly storage = inject(TokenStorageService);
  private readonly router = inject(Router);

  private readonly authenticatingState = signal(false);
  private readonly verifiedState = signal(false);

  /** Intentos fallidos dentro de la ventana vigente. */
  private readonly attemptsState = signal(0);
  private readonly lockUntilState = signal<number | null>(null);
  private readonly clockState = signal(Date.now());
  private readonly failures: number[] = [];
  private ticker: ReturnType<typeof setInterval> | null = null;

  readonly token = this.storage.token;
  readonly accessToken = this.storage.token;
  readonly user = this.storage.user;
  readonly permissions = this.storage.permissions;
  readonly authenticating = this.authenticatingState.asReadonly();
  readonly isVerified = this.verifiedState.asReadonly();
  readonly failedAttempts = this.attemptsState.asReadonly();

  readonly isAuthenticated = computed(
    () => this.storage.token() !== null && this.storage.user() !== null,
  );
  readonly role = computed<UserRole | null>(() => this.storage.user()?.role ?? null);
  readonly remainingAttempts = computed(() => Math.max(0, RATE_LIMIT_MAX - this.attemptsState()));

  /** Segundos restantes de bloqueo (0 si no está bloqueado). */
  readonly lockRemainingSeconds = computed(() => {
    const until = this.lockUntilState();
    return until ? Math.max(0, Math.ceil((until - this.clockState()) / 1000)) : 0;
  });
  readonly isLockedOut = computed(() => this.lockRemainingSeconds() > 0);

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

  /**
   * Autentica contra `POST /auth/login`, persiste el JWT y navega a la ruta
   * inicial del rol (`ROLE_HOME`), salvo que la navegación traiga `returnUrl`.
   */
  login(credentials: LoginCredentials): Observable<CurrentUserResponse> {
    if (this.isLockedOut()) {
      return throwError(
        () => new Error(`Demasiados intentos fallidos. Espera ${this.lockRemainingSeconds()} s.`),
      );
    }

    const payload: LoginRequest = {
      email: credentials.email.trim(),
      password: credentials.password,
    };
    this.authenticatingState.set(true);
    return this.post<TokenResponse>(API_ENDPOINTS.auth.login, payload).pipe(
      tap((response) => {
        this.storage.save(response, credentials.remember);
        this.verifiedState.set(true);
        this.resetAttempts();
        void this.router.navigateByUrl(
          credentials.returnUrl ?? ROLE_HOME[response.user.role],
        );
      }),
      map((response): CurrentUserResponse => ({
        ...response.user,
        permissions: response.permissions,
      })),
      catchError((error: unknown) => {
        if (isApiError(error) && error.status === 401) {
          this.registerFailure();
        }
        return throwError(() => error);
      }),
      finalize(() => this.authenticatingState.set(false)),
    );
  }

  /**
   * Revoca la sesión en el backend (best-effort) y limpia el estado local.
   * La navegación al login es inmediata: no se espera la respuesta del servidor.
   */
  logout(redirectToLogin = true): void {
    if (this.storage.token()) {
      this.post<void>(API_ENDPOINTS.auth.logout)
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
    return this.get<CurrentUserResponse>(API_ENDPOINTS.auth.me).pipe(
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

  /** Registra un intento fallido y activa el bloqueo al superar el máximo. */
  registerFailure(): void {
    const now = Date.now();
    const recent = this.failures.filter((attempt) => now - attempt < RATE_LIMIT_WINDOW_MS);
    recent.push(now);
    this.failures.length = 0;
    this.failures.push(...recent);

    if (recent.length >= RATE_LIMIT_MAX) {
      this.failures.length = 0;
      this.attemptsState.set(0);
      this.lockUntilState.set(now + LOCKOUT_MS);
      this.clockState.set(now);
      this.startLockoutTicker();
      return;
    }
    this.attemptsState.set(recent.length);
  }

  resetAttempts(): void {
    this.stopLockoutTicker();
    this.failures.length = 0;
    this.attemptsState.set(0);
    this.lockUntilState.set(null);
  }

  clearSession(): void {
    this.storage.clear();
    this.verifiedState.set(false);
  }

  /** Usado por `authInterceptor` ante un 401 de una sesión ya iniciada. */
  handleSessionExpired(): void {
    this.clearSession();
    void this.router.navigate([APP_ROUTES.login], {
      queryParams: { reason: SESSION_EXPIRED_REASON },
    });
  }

  private startLockoutTicker(): void {
    this.stopLockoutTicker();
    this.ticker = setInterval(() => {
      this.clockState.set(Date.now());
      const until = this.lockUntilState();
      if (until !== null && Date.now() >= until) {
        this.lockUntilState.set(null);
        this.stopLockoutTicker();
      }
    }, 1_000);
  }

  private stopLockoutTicker(): void {
    if (this.ticker !== null) {
      clearInterval(this.ticker);
      this.ticker = null;
    }
  }
}

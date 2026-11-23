import { HttpErrorResponse } from '@angular/common/http';
import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import {
  catchError,
  finalize,
  map,
  of,
  switchMap,
  tap,
  throwError,
  type Observable,
} from 'rxjs';
import { BaseApi } from '../../api/api-url';
import { API_ENDPOINTS } from '../../api/endpoints';
import {
  LOCKOUT_MS,
  RATE_LIMIT_MAX,
  RATE_LIMIT_WINDOW_MS,
} from '../../constants/auth-rate-limit';
import {
  AUTH_STORAGE_KEYS,
  type StoragePersistence,
} from '../../constants/auth-storage';
import { APP_ROUTES, ROLE_HOME, SESSION_EXPIRED_REASON } from '../../constants/nav';
import { isApiError } from '../../models/error';
import type {
  CurrentUserOut,
  LoginCredentials,
  LoginRequest,
  LoginResponse,
  Permission,
  UserOut,
  UserRole,
} from '../../models/user';

/** La sesión cambió en otra pestaña y la petición ya no es válida. */
export class SessionChangedError extends HttpErrorResponse {
  constructor(message = 'La sesión cambió en otra pestaña. Vuelve a iniciar sesión.') {
    super({
      status: 409,
      statusText: 'Conflict',
      error: {
        success: false,
        error: { code: 'SESSION_CHANGED', message },
      },
    });
  }
}

interface PersistedSession {
  readonly token: string;
  readonly expiresAt: number;
  readonly user: CurrentUserOut;
}

/**
 * Única fuente de verdad de la sesión: hidrata los signals desde el
 * almacenamiento, expone estado derivado y ejecuta los endpoints `/auth/*`
 * que existen en `openapi.json` (login, logout y me).
 */
@Injectable({ providedIn: 'root' })
export class AuthService extends BaseApi {
  private readonly router = inject(Router);

  private readonly currentUserState = signal<CurrentUserOut | null>(null);
  private readonly tokenState = signal<string | null>(null);
  private readonly accessTokenExpiresAtState = signal<number | null>(null);

  private readonly authenticatingState = signal(false);
  private readonly verifiedState = signal(false);

  private readonly attemptsState = signal(0);
  private readonly lockUntilState = signal<number | null>(null);
  private readonly clockState = signal(Date.now());
  private readonly failures: number[] = [];
  private ticker: ReturnType<typeof setInterval> | null = null;

  private persistence: StoragePersistence = 'local';
  private sessionExpiredHandled = false;

  readonly currentUser = this.currentUserState.asReadonly();
  readonly accessToken = this.tokenState.asReadonly();
  readonly accessTokenExpiresAt = this.accessTokenExpiresAtState.asReadonly();

  readonly permissions = computed<readonly Permission[]>(
    () => this.currentUserState()?.permissions ?? [],
  );
  readonly role = computed<UserRole | null>(() => this.currentUserState()?.role ?? null);
  readonly isAuthenticated = computed(
    () => this.tokenState() !== null && this.currentUserState() !== null,
  );
  readonly isAdmin = computed(() => this.role() === 'ADMIN');
  readonly isOffice = computed(() => this.role() === 'OFFICE');
  readonly isAttendant = computed(() => this.role() === 'ATTENDANT');

  readonly fullName = computed(() => {
    const user = this.currentUserState();
    return user ? `${user.first_name} ${user.last_name}` : '';
  });
  readonly userInitials = computed(() =>
    this.fullName()
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase(),
  );
  readonly branchName = computed(
    () => this.currentUserState()?.branch?.name ?? 'Todas las sedes',
  );

  readonly authenticating = this.authenticatingState.asReadonly();
  readonly isVerified = this.verifiedState.asReadonly();
  readonly failedAttempts = this.attemptsState.asReadonly();
  readonly remainingAttempts = computed(() =>
    Math.max(0, RATE_LIMIT_MAX - this.attemptsState()),
  );

  /** Segundos restantes de bloqueo (0 si no está bloqueado). */
  readonly lockRemainingSeconds = computed(() => {
    const until = this.lockUntilState();
    return until ? Math.max(0, Math.ceil((until - this.clockState()) / 1000)) : 0;
  });
  readonly isLockedOut = computed(() => this.lockRemainingSeconds() > 0);

  constructor() {
    super();
    this.restore();
    inject(DestroyRef).onDestroy(() => this.stopLockoutTicker());
  }

  /**
   * Valida la sesión restaurada antes de que el Router evalúe los guards.
   * Sin `refresh_token` en `openapi.json`, un access token vencido se descarta.
   */
  initialize(): Observable<void> {
    const token = this.tokenState();
    const user = this.currentUserState();
    const expiresAt = this.accessTokenExpiresAtState();

    if (!token || !user || expiresAt === null) {
      this.clearSession();
      this.sessionExpiredHandled = false;
      return of(void 0);
    }

    if (expiresAt > Date.now()) {
      this.verifiedState.set(true);
      return of(void 0);
    }

    this.clearSession();
    return of(void 0);
  }

  /**
   * `POST /auth/login` con el body JSON exacto de `openapi.json`.
   * Si la respuesta no incluyera `user`, se completa con `GET /auth/me`.
   */
  login(credentials: LoginCredentials): Observable<CurrentUserOut> {
    const limited = this.checkRateLimit();
    if (limited) {
      return throwError(() => limited);
    }

    const payload: LoginRequest = {
      email: credentials.email.trim(),
      password: credentials.password,
    };

    this.authenticatingState.set(true);
    return this.post<LoginResponse>(API_ENDPOINTS.auth.login, payload).pipe(
      switchMap((response) =>
        response.user
          ? of(response)
          : this.me().pipe(map((user): LoginResponse => ({ ...response, user }))),
      ),
      map((response) => this.startSession(response, credentials.remember, credentials.returnUrl)),
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
   * Limpia el estado local de inmediato y revoca el token en el backend
   * (best-effort, sin esperar la respuesta).
   */
  logout(redirectToLogin = true): void {
    const token = this.tokenState();
    this.clearSession();
    this.sessionExpiredHandled = false;

    if (token) {
      this.postWithHeaders<void>(API_ENDPOINTS.auth.logout, {}, {
        Authorization: `Bearer ${token}`,
      })
        .pipe(catchError(() => of(undefined)))
        .subscribe({ error: () => undefined });
    }

    if (redirectToLogin) {
      void this.router.navigate([APP_ROUTES.login]);
    }
  }

  /** `GET /auth/me`: refresca usuario y permisos de la sesión vigente. */
  me(): Observable<CurrentUserOut> {
    return this.get<CurrentUserOut>(API_ENDPOINTS.auth.me).pipe(
      tap((user) => this.updateUser(user)),
    );
  }

  /** Cierra la sesión una sola vez y redirige al login con el motivo. */
  handleSessionExpired(): void {
    if (this.sessionExpiredHandled) {
      return;
    }
    this.sessionExpiredHandled = true;
    this.clearSession();
    void this.router.navigate([APP_ROUTES.login], {
      queryParams: { reason: SESSION_EXPIRED_REASON },
    });
  }

  hasPermission(permission: Permission): boolean {
    return this.permissions().includes(permission);
  }

  /**
   * Rate limit local antes de tocar la red. Devuelve el `429` listo para
   * propagar, o `null` cuando se puede intentar el login.
   */
  checkRateLimit(): HttpErrorResponse | null {
    if (!this.isLockedOut()) {
      return null;
    }
    return new HttpErrorResponse({
      status: 429,
      statusText: 'Too Many Requests',
      error: {
        success: false,
        error: {
          code: 'RATE_LIMITED',
          message: `Demasiados intentos fallidos. Espera ${this.lockRemainingSeconds()} s.`,
        },
      },
    });
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
    this.remove('local');
    this.remove('session');
    this.setState(null, null, null);
    this.verifiedState.set(false);
  }

  private startSession(
    response: LoginResponse,
    remember: boolean,
    returnUrl?: string,
  ): CurrentUserOut {
    const user: CurrentUserOut = {
      ...response.user,
      permissions: response.permissions,
    };
    const expiresAt = Date.now() + response.expires_in * 1000;
    const persistence: StoragePersistence = remember ? 'local' : 'session';

    this.persistence = persistence;
    this.write(persistence, { token: response.access_token, expiresAt, user });
    this.setState(response.access_token, expiresAt, user);
    this.verifiedState.set(true);
    this.sessionExpiredHandled = false;
    this.resetAttempts();

    void this.router.navigateByUrl(returnUrl ?? ROLE_HOME[user.role]);
    return user;
  }

  private updateUser(user: CurrentUserOut): void {
    const token = this.tokenState();
    const expiresAt = this.accessTokenExpiresAtState();
    if (!token || expiresAt === null) {
      return;
    }
    this.write(this.persistence, { token, expiresAt, user });
    this.currentUserState.set(user);
    this.verifiedState.set(true);
  }

  private restore(): void {
    const session = this.read('session') ?? this.read('local');
    if (!session) {
      this.clearSession();
      return;
    }
    this.persistence = this.read('session') ? 'session' : 'local';
    this.setState(session.token, session.expiresAt, session.user);
  }

  private setState(
    token: string | null,
    expiresAt: number | null,
    user: CurrentUserOut | null,
  ): void {
    this.tokenState.set(token);
    this.accessTokenExpiresAtState.set(expiresAt);
    this.currentUserState.set(user);
  }

  private read(kind: StoragePersistence): PersistedSession | null {
    const storage = this.storage(kind);
    if (!storage) {
      return null;
    }
    try {
      const token = storage.getItem(AUTH_STORAGE_KEYS.accessToken);
      const expiresAt = Number(storage.getItem(AUTH_STORAGE_KEYS.expiresAt) ?? 0);
      const rawUser = storage.getItem(AUTH_STORAGE_KEYS.session);
      if (!token || !rawUser || !expiresAt) {
        this.remove(kind);
        return null;
      }
      return {
        token,
        expiresAt,
        user: JSON.parse(rawUser) as CurrentUserOut,
      };
    } catch {
      this.remove(kind);
      return null;
    }
  }

  private write(kind: StoragePersistence, session: PersistedSession): void {
    const storage = this.storage(kind);
    if (!storage) {
      return;
    }
    try {
      storage.setItem(AUTH_STORAGE_KEYS.accessToken, session.token);
      storage.setItem(AUTH_STORAGE_KEYS.expiresAt, String(session.expiresAt));
      storage.setItem(AUTH_STORAGE_KEYS.session, JSON.stringify(session.user));
      storage.setItem(AUTH_STORAGE_KEYS.persistence, kind);
    } catch {
      // Almacenamiento lleno o bloqueado: la sesión sigue viva en memoria.
    }
  }

  private remove(kind: StoragePersistence): void {
    const storage = this.storage(kind);
    if (!storage) {
      return;
    }
    try {
      for (const key of Object.values(AUTH_STORAGE_KEYS)) {
        storage.removeItem(key);
      }
    } catch {
      // Nada que limpiar si el almacenamiento no está disponible.
    }
  }

  private storage(kind: StoragePersistence): Storage | null {
    try {
      return kind === 'local' ? window.localStorage : window.sessionStorage;
    } catch {
      return null;
    }
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

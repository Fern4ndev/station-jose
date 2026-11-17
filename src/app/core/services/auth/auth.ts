import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { map, Observable, tap } from 'rxjs';
import { API_BASE_URL } from '../../api/api-url';
import {
  AuthSession,
  CurrentUser,
  CurrentUserResponseDto,
  LoginRequest,
  LoginResponseDto,
  LoginResult,
  mapCurrentUserResponse,
  mapLoginResponse,
} from '../../models/auth.models';

@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = inject(API_BASE_URL);

  login(credentials: LoginRequest): Observable<LoginResult> {
    const request: LoginRequest = {
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password,
    };

    return this.http
      .post<LoginResponseDto>(`${this.apiBaseUrl}/auth/login`, request)
      .pipe(map(mapLoginResponse));
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.apiBaseUrl}/auth/logout`, null);
  }

  currentUser(): Observable<CurrentUser> {
    return this.http
      .get<CurrentUserResponseDto>(`${this.apiBaseUrl}/auth/me`)
      .pipe(map(mapCurrentUserResponse));
  }
}

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
      const returnUrl = this.router.url;
      this.clearSession();
      void this.router.navigate(['/auth/login'], { queryParams: { expired: 'true', returnUrl } });
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

@Injectable({ providedIn: 'root' })
export class AuthSessionService {
  private readonly api = inject(AuthApiService);
  private readonly store = inject(AuthStore);

  login(credentials: LoginRequest): Observable<LoginResult> {
    return this.api.login(credentials).pipe(tap((response) => this.store.setSession(response)));
  }

  logout(): Observable<void> {
    return this.api.logout();
  }
}

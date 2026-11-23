import { Injectable, computed, signal } from '@angular/core';
import { AUTH_STORAGE_KEYS, type StoragePersistence } from '../constants/auth-storage';
import type { CurrentUserResponse, Permission, TokenResponse } from '../models/auth.model';

interface PersistedSession {
  readonly token: string;
  readonly expiresAt: number;
  readonly user: CurrentUserResponse;
}

/**
 * Única capa que toca `localStorage`/`sessionStorage`.
 * Recuerda "Mantener la sesión en este equipo": local para sesiones recordadas,
 * session para las demás, y limpia ambas al cerrar sesión.
 */
@Injectable({ providedIn: 'root' })
export class TokenStorageService {
  private readonly tokenState = signal<string | null>(null);
  private readonly userState = signal<CurrentUserResponse | null>(null);
  private readonly permissionsState = signal<readonly Permission[]>([]);
  private readonly expiresAtState = signal<number | null>(null);
  private readonly persistenceState = signal<StoragePersistence>('local');

  readonly token = this.tokenState.asReadonly();
  readonly user = this.userState.asReadonly();
  readonly permissions = this.permissionsState.asReadonly();
  readonly expiresAt = this.expiresAtState.asReadonly();
  readonly persistence = this.persistenceState.asReadonly();
  readonly hasToken = computed(() => this.tokenState() !== null);

  constructor() {
    this.restore();
  }

  /** Guarda la sesión completa devuelta por `/auth/login`. */
  save(response: TokenResponse, remember: boolean): void {
    const user: CurrentUserResponse = {
      ...response.user,
      permissions: response.permissions,
    };
    const expiresAt = Date.now() + response.expires_in * 1000;
    const persistence: StoragePersistence = remember ? 'local' : 'session';

    this.write(persistence, {
      token: response.access_token,
      expiresAt,
      user,
    });
    this.setState(response.access_token, user, response.permissions, expiresAt, persistence);
  }

  /** Refresca el usuario cuando `/auth/me` devuelve datos más recientes. */
  updateUser(user: CurrentUserResponse): void {
    const token = this.tokenState();
    const expiresAt = this.expiresAtState();
    if (!token || !expiresAt) {
      return;
    }
    this.write(this.persistenceState(), { token, expiresAt, user });
    this.userState.set(user);
    this.permissionsState.set(user.permissions);
  }

  clear(): void {
    this.remove('local');
    this.remove('session');
    this.setState(null, null, [], null, 'local');
  }

  private restore(): void {
    const session = this.read('session') ?? this.read('local');
    if (!session) {
      this.clear();
      return;
    }
    const persistence: StoragePersistence = this.read('session') ? 'session' : 'local';
    this.setState(
      session.token,
      session.user,
      session.user.permissions,
      session.expiresAt,
      persistence,
    );
  }

  private setState(
    token: string | null,
    user: CurrentUserResponse | null,
    permissions: readonly Permission[],
    expiresAt: number | null,
    persistence: StoragePersistence,
  ): void {
    this.tokenState.set(token);
    this.userState.set(user);
    this.permissionsState.set(permissions);
    this.expiresAtState.set(expiresAt);
    this.persistenceState.set(persistence);
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
      if (!token || !rawUser || !expiresAt || expiresAt <= Date.now()) {
        this.remove(kind);
        return null;
      }
      return {
        token,
        expiresAt,
        user: JSON.parse(rawUser) as CurrentUserResponse,
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
      // Ignorado: no hay nada que limpiar si el almacenamiento no está disponible.
    }
  }

  private storage(kind: StoragePersistence): Storage | null {
    try {
      return kind === 'local' ? window.localStorage : window.sessionStorage;
    } catch {
      return null;
    }
  }
}

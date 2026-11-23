import { Injectable, signal } from '@angular/core';
import { finalize, tap, type Observable } from 'rxjs';
import { BaseApi } from '../api/api-url';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  UserCreate,
  UserListQuery,
  UserListResponse,
  UserResponse,
  UserRoleUpdate,
  UserStatusUpdate,
  UserUpdate,
} from '../models/user.model';

/** Usuarios: listado paginado y mutaciones, con caché reactiva del listado. */
@Injectable({ providedIn: 'root' })
export class UsersService extends BaseApi {
  private readonly loadingState = signal(false);
  private readonly itemsState = signal<readonly UserResponse[]>([]);
  private readonly totalState = signal(0);
  private readonly selectedState = signal<UserResponse | null>(null);

  readonly loading = this.loadingState.asReadonly();
  readonly users = this.itemsState.asReadonly();
  readonly total = this.totalState.asReadonly();
  readonly selected = this.selectedState.asReadonly();

  list(query: UserListQuery = {}): Observable<UserListResponse> {
    this.loadingState.set(true);
    return this.get<UserListResponse>(API_ENDPOINTS.users.base, query).pipe(
      tap((response) => {
        this.itemsState.set(response.items);
        this.totalState.set(response.pagination.total);
      }),
      finalize(() => this.loadingState.set(false)),
    );
  }

  detail(userId: string): Observable<UserResponse> {
    this.loadingState.set(true);
    return this.get<UserResponse>(API_ENDPOINTS.users.byId(userId)).pipe(
      tap((user) => this.selectedState.set(user)),
      finalize(() => this.loadingState.set(false)),
    );
  }

  create(payload: UserCreate): Observable<UserResponse> {
    return this.post<UserResponse>(API_ENDPOINTS.users.base, payload).pipe(
      tap((user) => {
        this.itemsState.update((users) => [...users, user]);
        this.totalState.update((total) => total + 1);
      }),
    );
  }

  update(userId: string, payload: UserUpdate): Observable<UserResponse> {
    return this.patch<UserResponse>(API_ENDPOINTS.users.byId(userId), payload).pipe(
      tap((user) => this.sync(user)),
    );
  }

  updateRole(userId: string, payload: UserRoleUpdate): Observable<UserResponse> {
    return this.patch<UserResponse>(API_ENDPOINTS.users.role(userId), payload).pipe(
      tap((user) => this.sync(user)),
    );
  }

  updateStatus(userId: string, payload: UserStatusUpdate): Observable<UserResponse> {
    return this.patch<UserResponse>(API_ENDPOINTS.users.status(userId), payload).pipe(
      tap((user) => this.sync(user)),
    );
  }

  private sync(updated: UserResponse): void {
    this.itemsState.update((users) =>
      users.map((user) => (user.id === updated.id ? updated : user)),
    );
    if (this.selectedState()?.id === updated.id) {
      this.selectedState.set(updated);
    }
  }
}

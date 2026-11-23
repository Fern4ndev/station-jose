import { Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { API_ENDPOINTS, BaseApi } from '../api/api-url';
import type {
  UserCreate,
  UserListQuery,
  UserListResponse,
  UserOut,
  UserRoleUpdate,
  UserStatusUpdate,
  UserUpdate,
} from '../models/user';

/** Usuarios: listado paginado y mutaciones. Sin estado local. */
@Injectable({ providedIn: 'root' })
export class UsersApi extends BaseApi {
  list(query: UserListQuery = {}): Observable<UserListResponse> {
    return this.get<UserListResponse>(API_ENDPOINTS.users.base, query);
  }

  detail(userId: string): Observable<UserOut> {
    return this.get<UserOut>(API_ENDPOINTS.users.byId(userId));
  }

  create(payload: UserCreate): Observable<UserOut> {
    return this.post<UserOut>(API_ENDPOINTS.users.base, payload);
  }

  update(userId: string, payload: UserUpdate): Observable<UserOut> {
    return this.patch<UserOut>(API_ENDPOINTS.users.byId(userId), payload);
  }

  updateRole(userId: string, payload: UserRoleUpdate): Observable<UserOut> {
    return this.patch<UserOut>(API_ENDPOINTS.users.role(userId), payload);
  }

  updateStatus(userId: string, payload: UserStatusUpdate): Observable<UserOut> {
    return this.patch<UserOut>(API_ENDPOINTS.users.status(userId), payload);
  }
}

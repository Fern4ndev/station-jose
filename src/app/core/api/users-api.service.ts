import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type {
  UserCreate,
  UserListQuery,
  UserListResponse,
  UserResponse,
  UserRoleUpdate,
  UserStatusUpdate,
  UserUpdate,
} from '../models/user.model';
import { toHttpParams } from './http-params';

@Injectable({ providedIn: 'root' })
export class UsersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  list(query: UserListQuery = {}): Observable<UserListResponse> {
    return this.http.get<UserListResponse>(`${this.baseUrl}${API_ENDPOINTS.users.base}`, {
      params: toHttpParams(query),
    });
  }

  get(userId: string): Observable<UserResponse> {
    return this.http.get<UserResponse>(`${this.baseUrl}${API_ENDPOINTS.users.byId(userId)}`);
  }

  create(payload: UserCreate): Observable<UserResponse> {
    return this.http.post<UserResponse>(`${this.baseUrl}${API_ENDPOINTS.users.base}`, payload);
  }

  update(userId: string, payload: UserUpdate): Observable<UserResponse> {
    return this.http.patch<UserResponse>(
      `${this.baseUrl}${API_ENDPOINTS.users.byId(userId)}`,
      payload,
    );
  }

  updateRole(userId: string, payload: UserRoleUpdate): Observable<UserResponse> {
    return this.http.patch<UserResponse>(
      `${this.baseUrl}${API_ENDPOINTS.users.role(userId)}`,
      payload,
    );
  }

  updateStatus(userId: string, payload: UserStatusUpdate): Observable<UserResponse> {
    return this.http.patch<UserResponse>(
      `${this.baseUrl}${API_ENDPOINTS.users.status(userId)}`,
      payload,
    );
  }
}

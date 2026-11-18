import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { API_BASE_URL } from '../../core/api/api-url';
import { mapAuthenticatedUser } from '../../core/models/auth.models';
import type { AuthenticatedUser, AuthenticatedUserDto, UserManagementRole } from '../../core/models/auth.models';

export interface CreateUserRequest {
  readonly first_name: string;
  readonly last_name: string;
  readonly dni: string;
  readonly email: string;
  readonly password: string;
  readonly role: UserManagementRole;
  readonly branch_id: string | null;
}

export interface UsersPageResult {
  readonly items: readonly AuthenticatedUser[];
  readonly pagination: { readonly page: number; readonly pages: number; readonly total: number };
}

@Injectable({ providedIn: 'root' })
export class UsersApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);
  list(page: number): Observable<UsersPageResult> {
    return this.http.get<{ items: AuthenticatedUserDto[]; pagination: UsersPageResult['pagination'] }>(`${this.baseUrl}/users`, {
      params: new HttpParams().set('page', page).set('page_size', 20),
    }).pipe(map((result) => ({ ...result, items: result.items.map(mapAuthenticatedUser) })));
  }
  get(id: string): Observable<AuthenticatedUser> {
    return this.http.get<AuthenticatedUserDto>(`${this.baseUrl}/users/${encodeURIComponent(id)}`).pipe(map(mapAuthenticatedUser));
  }
  create(request: CreateUserRequest): Observable<AuthenticatedUser> {
    return this.http.post<AuthenticatedUserDto>(`${this.baseUrl}/users`, request).pipe(map(mapAuthenticatedUser));
  }
  update(id: string, firstName: string, lastName: string): Observable<AuthenticatedUser> {
    return this.http.patch<AuthenticatedUserDto>(`${this.baseUrl}/users/${encodeURIComponent(id)}`, { first_name: firstName, last_name: lastName }).pipe(map(mapAuthenticatedUser));
  }
  setRole(id: string, role: UserManagementRole, branchId: string | null): Observable<AuthenticatedUser> {
    return this.http.patch<AuthenticatedUserDto>(`${this.baseUrl}/users/${encodeURIComponent(id)}/role`, { role, branch_id: branchId }).pipe(map(mapAuthenticatedUser));
  }
  setStatus(id: string, active: boolean): Observable<AuthenticatedUser> {
    return this.http.patch<AuthenticatedUserDto>(`${this.baseUrl}/users/${encodeURIComponent(id)}/status`, { is_active: active }).pipe(map(mapAuthenticatedUser));
  }
}

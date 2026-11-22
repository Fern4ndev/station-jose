import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../constants/api.constants';
import type {
  CurrentUserResponse,
  LoginRequest,
  TokenResponse,
} from '../models/auth.model';

@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  login(payload: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}${API_ENDPOINTS.auth.login}`, payload);
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}${API_ENDPOINTS.auth.logout}`, {});
  }

  me(): Observable<CurrentUserResponse> {
    return this.http.get<CurrentUserResponse>(`${this.baseUrl}${API_ENDPOINTS.auth.me}`);
  }
}

import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { API_BASE_URL } from '../api/api.config';
import {
  CurrentUser,
  CurrentUserResponseDto,
  LoginRequest,
  LoginResponseDto,
  LoginResult,
  mapCurrentUserResponse,
  mapLoginResponse,
} from './auth.models';

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

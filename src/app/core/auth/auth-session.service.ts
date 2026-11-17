import { inject, Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { AuthApiService } from './auth-api.service';
import { AuthStore } from './auth.store';
import { LoginRequest, LoginResult } from './auth.models';

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

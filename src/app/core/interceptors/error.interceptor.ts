import type { HttpInterceptorFn } from '@angular/common/http';
import { Injector, inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { toApiError } from '../api/api-error';
import { API_ENDPOINTS } from '../constants/api.constants';
import { AuthService } from '../services/auth.service';

/**
 * Convierte cualquier `HttpErrorResponse` en el `ApiError` normalizado
 * (`{ status, code, message, validation }`) y cierra la sesión ante un 401
 * distinto del propio login fallido.
 */
export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  // `inject(Injector)` evita un ciclo AuthService → AuthApiService → HttpClient.
  const injector = inject(Injector);

  return next(request).pipe(
    catchError((error: unknown) => {
      const apiError = toApiError(error);
      const isLoginRequest = request.url.endsWith(API_ENDPOINTS.auth.login);

      if (apiError.status === 401 && !isLoginRequest) {
        injector.get(AuthService).expireSession();
      }

      return throwError(() => apiError);
    }),
  );
};

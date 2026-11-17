import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthStore } from '../services/auth/auth';
import { API_BASE_URL } from '../api/api-url';
import { isApiRequest } from '../api/api-request';

export const apiErrorInterceptor: HttpInterceptorFn = (request, next) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);
  const isApi = isApiRequest(request.url, inject(API_BASE_URL));

  return next(request).pipe(
    catchError((error: unknown) => {
      if (isApi && error instanceof HttpErrorResponse && error.status === 401 && !request.url.endsWith('/auth/login')) {
        const isLoginRequest = request.url.endsWith('/auth/login');
        const hadSession = authStore.isAuthenticated();
        authStore.clearSession();

        if (hadSession && !isLoginRequest) {
          void router.navigate(['/auth/login'], {
            queryParams: { expired: 'true', returnUrl: router.url },
          });
        }
      }

      if (isApi && error instanceof HttpErrorResponse && error.status === 403) {
        void router.navigateByUrl('/access-denied');
      }

      return throwError(() => error);
    }),
  );
};

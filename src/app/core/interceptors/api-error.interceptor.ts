import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthStore } from '../services/auth/auth';

export const apiErrorInterceptor: HttpInterceptorFn = (request, next) => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        const isLoginRequest = request.url.endsWith('/auth/login');
        const hadSession = authStore.isAuthenticated();
        authStore.clearSession();

        if (hadSession && !isLoginRequest) {
          void router.navigate(['/auth/login'], {
            queryParams: { expired: 'true', returnUrl: router.url },
          });
        }
      }

      if (error instanceof HttpErrorResponse && error.status === 403) {
        void router.navigateByUrl('/access-denied');
      }

      return throwError(() => error);
    }),
  );
};

import type { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { TokenStorageService } from '../services/token-storage.service';

/** Adjunta `Authorization: Bearer <token>` solo a las llamadas a la API. */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(TokenStorageService).token();
  if (!token || !isApiRequest(request.url)) {
    return next(request);
  }
  return next(
    request.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    }),
  );
};

const isApiRequest = (url: string): boolean =>
  url.startsWith(environment.apiUrl) || url.startsWith('/api/');

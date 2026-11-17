import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthStore } from '../services/auth/auth';
import { API_BASE_URL } from '../api/api-url';
import { isApiRequest } from '../api/api-request';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(AuthStore).accessToken();
  const isLoginRequest = request.url.endsWith('/auth/login');

  if (!token || isLoginRequest || !isApiRequest(request.url, inject(API_BASE_URL))) {
    return next(request);
  }

  return next(request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};

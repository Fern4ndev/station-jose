import {
  ApplicationConfig,
  LOCALE_ID,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { providePrimeNG } from 'primeng/config';
import aura from '@primeuix/themes/aura';
import { MessageService } from 'primeng/api';
import { authInterceptor } from './core/interceptors/auth';
import { AuthService } from './core/services/auth/auth';

registerLocaleData(localeEs);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    provideAppInitializer(() => inject(AuthService).initialize()),
    { provide: LOCALE_ID, useValue: 'es' },
    providePrimeNG({
      theme: {
        preset: aura,
        options: {
          darkModeSelector: '.dark',
        },
      },
    }),
    MessageService,
  ],
};

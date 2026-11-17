import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import { providePrimeNG } from 'primeng/config';
import { routes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';
import { apiErrorInterceptor } from './core/auth/api-error.interceptor';

const SanJoseTheme = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#f2f5fc',
      100: '#e2e9f8',
      200: '#cbd8f2',
      300: '#a6bee9',
      400: '#7a9cdd',
      500: '#557ad1',
      600: '#395cc1',
      700: '#1f3975',
      800: '#1b3163',
      900: '#192b53',
      950: '#111c37',
    },
  },
});

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor, apiErrorInterceptor])),
    providePrimeNG({
      theme: {
        preset: SanJoseTheme,
        options: {
          cssLayer: {
            name: 'primeng',
            order: 'theme, base, primeng, components, utilities',
          },
        },
      },
    }),
  ],
};

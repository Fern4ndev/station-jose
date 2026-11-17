import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  selector: 'app-access-denied',
  template: `
    <main class="grid min-h-screen place-items-center bg-slate-50 px-5 py-12">
      <section class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-sm" aria-labelledby="access-title">
        <p class="text-sm font-semibold text-primary-600">Acceso restringido</p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950" id="access-title">No tienes permiso para esta sección</h1>
        <p class="mt-3 text-sm leading-6 text-slate-600">Tu cuenta no cuenta con el permiso necesario. Si crees que es un error, comunícate con el Administrador.</p>
        <a class="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary-700 px-4 text-sm font-semibold text-white hover:bg-primary-900" routerLink="/app">Volver a mi espacio</a>
      </section>
    </main>
  `,
})
export class AccessDeniedPage {}

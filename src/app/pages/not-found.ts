import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  selector: 'app-not-found',
  template: `
    <main class="grid min-h-screen place-items-center bg-slate-50 px-5 py-12">
      <section class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-sm" aria-labelledby="not-found-title">
        <p class="text-sm font-semibold text-primary-600">Error 404</p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950" id="not-found-title">No encontramos esta página</h1>
        <p class="mt-3 text-sm leading-6 text-slate-600">Revisa la dirección o vuelve a la página de inicio.</p>
        <a class="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary-700 px-4 text-sm font-semibold text-white hover:bg-primary-900" routerLink="/">Volver al inicio</a>
      </section>
    </main>
  `,
})
export class NotFoundPage {}

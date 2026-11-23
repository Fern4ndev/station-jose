import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  selector: 'app-not-found',
  template: `
    <section class="mx-auto flex max-w-[520px] flex-col items-center gap-[10px] py-[64px] text-center">
      <p class="m-0 text-[42px] font-semibold leading-none text-[#17343c]">404</p>
      <h1 class="m-0 text-[16px] font-semibold text-[#17343c]">Página no encontrada</h1>
      <p class="m-0 text-[12px] leading-[1.6] text-[#54666c]">
        La ruta que buscas no existe o fue movida a otra sección del panel.
      </p>
      <a class="sanjose-button sanjose-button--primary mt-[6px]" routerLink="/">Volver al panel</a>
    </section>
  `,
})
export class NotFound {}

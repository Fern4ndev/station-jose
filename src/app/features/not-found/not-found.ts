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
      <a class="inline-flex min-h-[39px] items-center justify-center gap-[8px] rounded-[11px] border border-transparent px-[13px] text-[11px] font-[620] whitespace-nowrap transition-[background,box-shadow] focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[rgba(57,198,174,0.72)] bg-(--sanjose-primary-action) text-white shadow-[0_5px_12px_rgba(23,60,66,0.13)] hover:bg-(--sanjose-primary-action-hover) mt-[6px]" routerLink="/">Volver al panel</a>
    </section>
  `,
})
export class NotFound {}

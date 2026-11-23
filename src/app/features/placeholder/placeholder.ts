import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Vista provisional para rutas declaradas en `nav.ts` que todavía no tienen
 * endpoint en `openapi.json` (o cuyo módulo aún no se conecta).
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-placeholder',
  template: `
    <section class="mx-auto flex max-w-[520px] flex-col items-center gap-[10px] py-[64px] text-center">
      <h1 class="m-0 text-[16px] font-semibold text-[#17343c]">{{ title() }}</h1>
      <p class="m-0 text-[12px] leading-[1.6] text-[#54666c]">
        {{ description() }}
      </p>
    </section>
  `,
})
export class Placeholder {
  readonly title = input('Módulo en preparación');
  readonly description = input('Esta sección aún no está disponible.');
}

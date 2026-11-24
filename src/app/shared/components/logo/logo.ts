import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type LogoTone = 'mint' | 'solid';

/**
 * Isotipo de la estación. Reutiliza el mismo trazo del mockup y solo cambia el
 * contenedor: `mint` para fondos oscuros (sidebar/login) y `solid` para móvil.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-logo',
  template: `
    <span [class]="toneClasses()" [style.width.px]="size()" [style.height.px]="size()" aria-hidden="true">
      <svg [attr.viewBox]="'0 0 24 24'" [attr.width]="iconSize()" [attr.height]="iconSize()" fill="none">
        <path
          d="M5 19V6.8C5 5.25 6.25 4 7.8 4h5.4C14.75 4 16 5.25 16 6.8V19M3.5 19h14M8 8h5M8 11h5"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
        />
        <path
          d="M16 8.5h2.1a1.4 1.4 0 0 1 1.4 1.4v5.6a1.5 1.5 0 0 0 3 0v-4.1l-2.2-2.2"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <path
          d="M8.2 19v-3.1a2.3 2.3 0 0 1 4.6 0V19"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
        />
      </svg>
    </span>
  `,
})
export class Logo {
  readonly size = input(40);
  readonly tone = input<LogoTone>('mint');

  protected readonly iconSize = computed(() => Math.round(this.size() * 0.55));

  protected readonly toneClasses = computed(() =>
    this.tone() === 'solid'
      ? 'grid flex-none place-items-center rounded-[12px] bg-[linear-gradient(145deg,#2a4c93,#1f3975)] text-white'
      : 'grid flex-none place-items-center rounded-[14px] border border-[rgba(255,255,255,0.28)] bg-[linear-gradient(145deg,rgba(75,204,180,0.31),rgba(73,118,127,0.2))] text-[#8be4d2] shadow-[inset_0_1px_rgba(255,255,255,0.21)]',
  );
}

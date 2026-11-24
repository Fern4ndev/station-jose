import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type AlertTone = 'error' | 'warn' | 'info' | 'success';

const TONE_CLASSES: Readonly<Record<AlertTone, string>> = {
  error: 'border-[#f0d4c4] bg-[#fdf3ec] text-[#9a5a2c]',
  warn: 'border-[#f2e2c4] bg-[#fdf8ec] text-[#8a6420]',
  info: 'border-[#d7e6ec] bg-[#f1f7f9] text-[#3f6675]',
  success: 'border-[#cfe9dd] bg-[#f0faf5] text-[#2f6d59]',
};

/** Mensaje en línea para errores de formulario y avisos de negocio. */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-alert',
  template: `
    <p
      class="m-0 rounded-[10px] border px-[11px] py-[9px] text-[10px] leading-[1.5]"
      [class]="toneClasses()"
      [attr.role]="tone() === 'error' ? 'alert' : 'status'"
      [attr.aria-live]="tone() === 'error' ? 'assertive' : 'polite'"
    >
      <ng-content />
    </p>
  `,
})
export class UiAlert {
  readonly tone = input<AlertTone>('error');

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}

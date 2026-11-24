import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'text';

const BASE_CLASSES =
  'inline-flex items-center justify-center gap-[8px] font-[620] whitespace-nowrap transition-[background,box-shadow] focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[rgba(57,198,174,0.72)] disabled:cursor-not-allowed disabled:opacity-60';

const VARIANT_CLASSES: Readonly<Record<ButtonVariant, string>> = {
  primary: `${BASE_CLASSES} min-h-[39px] rounded-[11px] border border-transparent bg-(--sanjose-primary-action) px-[13px] text-[11px] text-white shadow-[0_5px_12px_rgba(23,60,66,0.13)] enabled:hover:bg-(--sanjose-primary-action-hover)`,
  secondary: `${BASE_CLASSES} min-h-[39px] rounded-[11px] border border-[#dce5e6] bg-[rgba(255,255,255,0.72)] px-[13px] text-[11px] text-[#53656a] enabled:hover:bg-white`,
  danger: `${BASE_CLASSES} min-h-[39px] rounded-[11px] border border-transparent bg-[#a2412c] px-[13px] text-[11px] text-white shadow-[0_5px_12px_rgba(120,44,28,0.16)] enabled:hover:bg-[#8c3524]`,
  text: `${BASE_CLASSES} min-h-[30px] cursor-pointer border-0 bg-transparent px-[4px] text-[10px] text-(--sanjose-accent)`,
};

/**
 * Botón del mockup. Envuelve el `<button>` nativo con las clases del sistema
 * visual, de modo que `(click)` sigue burbujeando desde el host.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-button',
  template: `
    <button
      [type]="type()"
      [class]="classes()"
      [disabled]="disabled() || loading()"
      [attr.aria-busy]="loading()"
    >
      @if (loading()) {
        <span
          class="inline-block h-[12px] w-[12px] animate-spin rounded-[50%] border-2 border-current border-t-transparent"
          aria-hidden="true"
        ></span>
      }
      <ng-content />
    </button>
  `,
})
export class UiButton {
  readonly variant = input<ButtonVariant>('primary');
  readonly type = input<'button' | 'submit' | 'reset'>('button');
  readonly disabled = input(false);
  readonly loading = input(false);

  protected readonly classes = computed(() => VARIANT_CLASSES[this.variant()]);
}

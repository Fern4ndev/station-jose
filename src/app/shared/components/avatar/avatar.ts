import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

/**
 * Avatar del mockup: si hay imagen la muestra y, ante cualquier error de
 * carga (o si no existe), cae en las iniciales con el degradado de marca.
 */
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-avatar',
  template: `
    @if (showImage()) {
      <img
        class="h-full w-full rounded-[inherit] object-cover"
        [src]="avatarUrl()"
        [alt]="name() || initials()"
        (error)="failed.set(true)"
      />
    } @else {
      <span class="select-none">{{ initials() }}</span>
    }
  `,
  host: {
    class:
      'grid flex-none place-items-center overflow-hidden rounded-[12px] bg-[linear-gradient(135deg,#edd6b0,#9ac9bc)] text-[11px] font-[750] text-[#16353a]',
    '[style.width.px]': 'size()',
    '[style.height.px]': 'size()',
    '[style.font-size.px]': 'fontSize()',
    '[attr.role]': '"img"',
    '[attr.aria-label]': 'name() || initials()',
  },
})
export class Avatar {
  readonly initials = input.required<string>();
  readonly name = input('');
  readonly avatarUrl = input<string | null>(null);
  readonly size = input(34);

  protected readonly failed = signal(false);
  protected readonly showImage = computed(() => Boolean(this.avatarUrl()) && !this.failed());
  protected readonly fontSize = computed(() => Math.max(9, Math.round(this.size() * 0.32)));
}

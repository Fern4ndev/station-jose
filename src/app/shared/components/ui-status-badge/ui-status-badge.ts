import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type StatusTone = 'green' | 'amber' | 'blue' | 'gray';

const TONE_CLASSES: Readonly<Record<StatusTone, string>> = {
  green: 'bg-[#e9f6f0] text-[#397f67]',
  amber: 'bg-[#fbf1e2] text-[#a76e24]',
  blue: 'bg-[#eaf2f6] text-[#4a768d]',
  gray: 'bg-[#edf0f0] text-[#6f7a7d]',
};

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-status-badge',
  templateUrl: './ui-status-badge.html',
})
export class UiStatusBadge {
  readonly label = input.required<string>();
  readonly tone = input<StatusTone>('green');

  protected readonly toneClasses = computed(() => TONE_CLASSES[this.tone()]);
}

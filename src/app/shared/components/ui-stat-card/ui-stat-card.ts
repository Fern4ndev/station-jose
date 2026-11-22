import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { UiIcon, type UiIconName } from '../ui-icon/ui-icon';

export type StatTone = 'mint' | 'amber';

/** Contenido de una tarjeta de métrica; lo comparten dashboard y reportes. */
export interface StatCardModel {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly suffix?: string;
  readonly note: string;
  readonly noteLead?: string;
  readonly icon: UiIconName;
  readonly tone: StatTone;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UiIcon],
  selector: 'app-ui-stat-card',
  templateUrl: './ui-stat-card.html',
})
export class UiStatCard {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly suffix = input('');
  readonly note = input('');
  readonly noteLead = input('');
  readonly icon = input.required<UiIconName>();
  readonly tone = input<StatTone>('mint');
}

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { GallonsDisplay } from '../gallons-display/gallons-display';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, imports: [GallonsDisplay], selector: 'app-balance-summary', templateUrl: './balance-summary.html' })
export class BalanceSummary {
  readonly authorized = input.required<string>();
  readonly attended = input.required<string>();
  readonly available = input.required<string>();
}

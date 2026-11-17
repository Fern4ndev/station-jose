import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-currency-display', templateUrl: './currency-display.html' })
export class CurrencyDisplay {
  readonly value = input.required<string>();
  readonly currency = input('PEN');
}

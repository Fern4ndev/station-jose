import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-gallons-display', templateUrl: './gallons-display.html' })
export class GallonsDisplay {
  readonly value = input.required<string>();
}

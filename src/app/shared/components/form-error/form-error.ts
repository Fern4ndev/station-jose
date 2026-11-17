import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-form-error', templateUrl: './form-error.html' })
export class FormError {
  readonly message = input<string | null>(null);
}

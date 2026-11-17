import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-api-error', templateUrl: './api-error.html' })
export class ApiError {
  readonly message = input.required<string>();
  readonly retry = output<void>();
}

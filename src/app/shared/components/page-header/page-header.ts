import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-page-header', styleUrl: './page-header.css', templateUrl: './page-header.html' })
export class PageHeader {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
}

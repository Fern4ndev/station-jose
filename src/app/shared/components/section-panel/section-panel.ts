import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({ changeDetection: ChangeDetectionStrategy.OnPush, selector: 'app-section-panel', styleUrl: './section-panel.css', templateUrl: './section-panel.html' })
export class SectionPanel {
  readonly title = input.required<string>();
  readonly description = input<string>('');
}

import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-page-heading',
  templateUrl: './ui-page-heading.html',
})
export class UiPageHeading {
  readonly title = input.required<string>();
  readonly subtitle = input('');
}

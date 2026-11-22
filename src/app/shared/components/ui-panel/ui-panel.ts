import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-ui-panel',
  templateUrl: './ui-panel.html',
})
export class UiPanel {
  readonly title = input('');
  readonly subtitle = input('');
}
